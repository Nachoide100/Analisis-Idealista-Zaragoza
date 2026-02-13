# 🏠 Zaragoza Real Estate Market Pulse: End-to-End Data Analysis

![Status](https://img.shields.io/badge/Status-Completed-success)
![Domain](https://img.shields.io/badge/Domain-Real%20Estate%20%26%20PropTech-blue)
![Role](https://img.shields.io/badge/Focus-Data%20Engineering%20%26%20BI-orange)

### 📋 Visión General del Proyecto
Este proyecto simula un entorno real de **Business Intelligence** aplicado al sector inmobiliario ("PropTech"). El objetivo principal es proporcionar una herramienta analítica para inversores que permita identificar **activos infravalorados ("chollos")** y analizar la rentabilidad de viviendas en Zaragoza, cruzando datos de mercado con variables socioeconómicas.

El flujo de trabajo abarca el ciclo de vida completo del dato: desde la ingeniería de extracción en entornos hostiles hasta el modelado dimensional en SQL y la visualización estratégica en Power BI.

---

### 🛠️ Tech Stack & Herramientas

| Categoría | Tecnologías Utilizadas |
| :--- | :--- |
| **Lenguaje** | ![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) |
| **ETL & Parsing** | ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-HTML%20Parsing-success) ![Pandas](https://img.shields.io/badge/Pandas-Data%20Cleaning-150458?logo=pandas&logoColor=white) |
| **Data Warehouse** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Star%20Schema-336791?logo=postgresql&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-Window%20Functions-CC2927?logo=microsoft-sql-server&logoColor=white) |
| **Visualization** | ![Power BI](https://img.shields.io/badge/Power%20BI-Advanced%20Dashboard-F2C811?logo=powerbi&logoColor=black) |
| **Version Control** | ![Git](https://img.shields.io/badge/Git-GitHub-F05032?logo=git&logoColor=white) |

---

### 🔄 Arquitectura del Proyecto (Workflow)

#### 1. Ingesta de Datos: Estrategia "Offline DOM Parsing"
El desafío principal fue la obtención de datos de fuentes inmobiliarias protegidas por sistemas anti-bot avanzados (Akamai/Datadome), que bloqueaban las peticiones automatizadas vía `Selenium` o `Requests`.

* **El Reto:** Bloqueo de IP (Error 403) ante peticiones secuenciales automatizadas.
* **La Solución (Ingeniería Resiliente):** Se diseñó un pipeline desacoplado en dos fases:
    1.  **Extracción Controlada:** Ingesta manual del código fuente renderizado (DOM Snapshot) a través de herramientas de desarrollo (DevTools) para simular tráfico 100% humano y asegurar la integridad de los datos.
    2.  **Parsing Automatizado:** Desarrollo de un algoritmo en **Python** con `BeautifulSoup` para procesar los archivos HTML locales, estructurando la información no estructurada (divs, spans, clases ofuscadas) en un dataset tabular limpio.

#### 2. Limpieza y Feature Engineering (Python & Pandas)
Transformación de datos crudos en métricas de negocio accionables:
* **Limpieza:** Normalización de cadenas de texto (Barrios compuestos), conversión de tipos de moneda y eliminación de duplicados.
* **Outlier Handling:** Aplicación de recorte lógico para eliminar valores extremos que sesgaban la media (mansiones o errores de precio).
* **Nuevas Métricas:**
    * `Precio_m2`: KPI estándar para comparativa equitativa.
    * `Es_Chollo (Algoritmo)`: Detección automática de oportunidades. Se utilizó la **Mediana** del barrio (más robusta que la media) para marcar inmuebles un 10% por debajo del valor de mercado.
    * `Data Enrichment`: Creación de la dimensión `dim_barrios` incorporando datos externos de Renta Media y un Índice de Seguridad Sintético.

#### 3. Data Warehousing (PostgreSQL)
Modelado de una base de datos relacional robusta (Star Schema) para alimentar el dashboard:
* **Esquema:** Tabla de hechos (`fact_inmuebles`) vinculada a tablas dimensionales (`dim_barrios`) con relación muchos a uno.

```sql
CREATE TABLE inmuebles(
	id_inmueble SERIAL PRIMARY KEY, 
    titulo TEXT,
    precio INT,
    habitaciones INT,
    metros INT,
    barrio_oficial VARCHAR(150),    
    es_outlier BOOLEAN,
    precio_m2 DECIMAL(10,2),
    tipo_vivienda VARCHAR(50),
    infravalorado BOOLEAN,          
    
    CONSTRAINT fk_barrio -- para cargar solo pisos que exista el barrio
        FOREIGN KEY (barrio_oficial) 
        REFERENCES dim_barrios(barrio_oficial)
)
```
```sql
CREATE TABLE dim_barrios (
    barrio_oficial VARCHAR(150) PRIMARY KEY, 
    distrito VARCHAR(100),
    renta_media DECIMAL(10,2),    
    seguridad_index DECIMAL(4,1), 
    latitud DECIMAL(10,6),       
    longitud DECIMAL(10,6)
);
```


* **Consultas Avanzadas:** Uso de **Vistas SQL** para pre-procesar cálculos complejos antes de llegar a Power BI, optimizando el rendimiento.
A continuación se presentan las 3 vistas clave creadas para la obtención de información clave de negocio:
1. Clasificación de barrios dentro de cada distrito según el precio por m2 ordenados de más caro a más barato.
```sql
CREATE VIEW vista_ranking_barrios AS 
SELECT 
    d.distrito,
    f.barrio_oficial,
    COUNT(f.id_inmueble) as oferta_disponible,
    ROUND(AVG(f.precio_m2), 0) as precio_m2_medio,
    d.renta_media,
    d.seguridad_index,
    -- Ranking: 1 = El barrio más caro de SU distrito
    RANK() OVER(PARTITION BY d.distrito ORDER BY AVG(f.precio_m2) DESC) as ranking_caro_distrito
FROM fact_inmuebles f
JOIN dim_barrios d ON f.barrio_oficial = d.barrio_oficial
GROUP BY d.distrito, f.barrio_oficial, d.renta_media, d.seguridad_index
ORDER BY d.distrito, ranking_caro_distrito;
```
2. Comparación del precio medio de inmuebles marcados como 'Infravalorados' frente al precio medio real del barrio al que pertenecen.
```sql
CREATE VIEW comparacion_real_chollo as 
SELECT 
    f.barrio_oficial,
    -- Precio medio del mercado "normal" (excluyendo chollos para no ensuciar)
    ROUND(AVG(CASE WHEN f.infravalorado = FALSE THEN f.precio END), 0) as precio_mercado,
    
    -- Precio medio de los "chollos"
    ROUND(AVG(CASE WHEN f.infravalorado = TRUE THEN f.precio END), 0) as precio_oportunidad,
    
    -- Margen Potencial (€)
    ROUND(
        AVG(CASE WHEN f.infravalorado = FALSE THEN f.precio END) - 
        AVG(CASE WHEN f.infravalorado = TRUE THEN f.precio END)
    , 0) as margen_bruto_medio,
    
    -- Cuántos chollos hay
    SUM(CASE WHEN f.infravalorado = TRUE THEN 1 ELSE 0 END) as n_chollos
FROM inmuebles f
GROUP BY f.barrio_oficial
HAVING SUM(CASE WHEN f.infravalorado = TRUE THEN 1 ELSE 0 END) > 0 -- Solo barrios con oportunidades
ORDER BY margen_bruto_medio DESC;
```
3. Cálculo de cantidad de sueldo íntegro necesario para que un vecino de un barrio se compre un piso ahí. Además, se añade columna de clasificación entre categorías según la cantidad:
* Gentrificación -> Más de 15 años.
* Oportunidad local -> Menos de 8 años.
* Resto -> Equilibrado.
```sql
WITH metricas_barrio AS (
    SELECT 
        f.barrio_oficial,
        AVG(f.precio) as precio_medio_zona,
        d.renta_media
    FROM fact_inmuebles f
    JOIN dim_barrios d ON f.barrio_oficial = d.barrio_oficial
    GROUP BY f.barrio_oficial, d.renta_media
)
SELECT 
    barrio_oficial,
    ROUND(precio_medio_zona, 0) as precio_medio,
    renta_media,
    -- Cálculo de años de esfuerzo
    ROUND(precio_medio_zona / NULLIF(renta_media, 0), 1) as anos_esfuerzo_fiscal,
    CASE 
        WHEN (precio_medio_zona / renta_media) > 15 THEN 'Gentrificación'
        WHEN (precio_medio_zona / renta_media) < 8 THEN 'Oportunidad Local'
        ELSE 'Equilibrado'
    END as estado_mercado
FROM metricas_barrio
ORDER BY anos_esfuerzo_fiscal DESC;
```

