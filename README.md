# 🏠 Zaragoza Real Estate Market Pulse: End-to-End Data Analysis

![Status](https://img.shields.io/badge/Status-Completed-success)
![Domain](https://img.shields.io/badge/Domain-Real%20Estate%20%26%20PropTech-blue)
![Role](https://img.shields.io/badge/Focus-Data%20Engineering%20%26%20BI-orange)

### 📋 Visión General del Proyecto

Este proyecto no nació en un laboratorio, sino de una necesidad real: ayudar a mi tía a encontrar piso en Zaragoza. El mercado inmobiliario es ruidoso; lleno de precios dispares y anuncios confusos que provocan parálisis por análisis.

Para resolverlo, cambié la intuición por el código. Traté su búsqueda como un problema de Ciencia de Datos, creando un algoritmo capaz de filtrar el ruido y responder a lo importante:

* **Precio Justo** 🏷️ ➤ Definir el valor real del m² por barrio.

* **Detección de Chollos** 💎 ➤ Identificar matemáticamente activos infravalorados.

* **Timing de Mercado** 📅 ➤ Validar el momento de compra.

El resultado fue pasar de la duda emocional a la seguridad de una decisión Data-Driven 📊.

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

### 1. Ingesta de Datos: Estrategia "Offline DOM Parsing"
El desafío principal fue la obtención de datos de fuentes inmobiliarias protegidas por sistemas anti-bot avanzados (Akamai/Datadome), que bloqueaban las peticiones automatizadas vía `Selenium` o `Requests`.

* **El Reto:** Bloqueo de IP (Error 403) ante peticiones secuenciales automatizadas.
* **La Solución (Ingeniería Resiliente):** Se diseñó un pipeline desacoplado en dos fases:
    1.  **Extracción Controlada:** Ingesta manual del código fuente renderizado (DOM Snapshot) a través de herramientas de desarrollo (DevTools) para simular tráfico 100% humano y asegurar la integridad de los datos.
    2.  **Parsing Automatizado:** Desarrollo de un algoritmo en **Python** con `BeautifulSoup` para procesar los archivos HTML locales, estructurando la información no estructurada (divs, spans, clases ofuscadas) en un dataset tabular limpio.

### 2. Limpieza y Feature Engineering (Python & Pandas)
Transformación de datos crudos en métricas de negocio accionables:
* **Limpieza:** Normalización de cadenas de texto (Barrios compuestos), conversión de tipos de moneda y eliminación de duplicados.
* **Outlier Handling:** Aplicación de recorte lógico para eliminar valores extremos que sesgaban la media (mansiones o errores de precio).
* **Análisis Variables target:** Añálisis distribución de valores, comparación mediana - media de las variables Precio y Precio_m2.

![nhisto](https://github.com/Nachoide100/Analisis-Idealista-Zaragoza/blob/a75e2b7d9bbaef97b5890346524a245e0f581751/visualizations/Captura%20de%20pantalla%202026-02-13%20093830.png)

### **Nuevas Métricas:**
* **Precio_m2:** KPI estándar para comparativa equitativa.
* **Es_Chollo (Algoritmo):** Detección automática de oportunidades. Se utilizó la **Mediana** del barrio (más robusta que la media) para marcar inmuebles un 10% por debajo del valor de mercado.
* **Tipo_vivienda:** Creación de la dimensión `tipo_vivienca` segmentando la muestra según el tipo de inmueble. 

### 3. Data Warehousing (PostgreSQL)
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
    -- Precio medio del mercado sin contar infravalorados
    ROUND(AVG(CASE WHEN f.infravalorado = FALSE THEN f.precio END), 0) as precio_mercado,
    
    -- Precio medio de los "infravalorados"
    ROUND(AVG(CASE WHEN f.infravalorado = TRUE THEN f.precio END), 0) as precio_oportunidad,
    
    -- Margen Potencial (€)
    ROUND(
        AVG(CASE WHEN f.infravalorado = FALSE THEN f.precio END) - 
        AVG(CASE WHEN f.infravalorado = TRUE THEN f.precio END)
    , 0) as margen_bruto_medio,
    
    -- Número de infravalorados
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
### 📊 Informe Interactivo (Power BI)

El resultado final es un informe estratégico de 4 páginas diseñado con enfoque UX, que guía al inversor desde la visión macro hasta el detalle del activo.

#### 1️⃣ Página 1: "Market Pulse" (Visión General)
**Objetivo:** Radiografía inmediata del estado del mercado.
* **Mapa de Calor Geoespacial:** Visualización de la densidad de precios sobre el mapa de Zaragoza, permitiendo identificar las "zonas calientes" de un vistazo.
* **KPIs Agregados:** Tarjetas dinámicas mostrando el volumen de oferta, precio medio del m² y niveles de renta media.
* **Ranking de Barrios:** Gráfico de barras que clasifica las zonas de mayor a menor exclusividad.

![informe1](https://github.com/Nachoide100/Analisis-Idealista-Zaragoza/blob/6be50519cf0e20a23cd5f7ad1b1c064fc422f4ff/visualizations/Captura%20de%20pantalla%202026-02-12%20195634.png)

#### 2️⃣ Página 2: "Strategic Drivers" (Análisis de Valor)
**Objetivo:** Entender las causas detrás del precio.
* **Matriz Seguridad-Precio:** Scatter Plot que cruza el coste del suelo con el índice de seguridad. Permite identificar **"Joyas Ocultas"** (Barrios seguros pero aún baratos).
* **Análisis de Correlación:** Gráfico de dispersión (Renta vs. Precio) con línea de tendencia para detectar zonas gentrificadas o infravaloradas respecto al poder adquisitivo de sus habitantes.
* **Segmentación:** Influencia de la cantidad de habitaciones en el precio de mercado. 

![informe2](https://github.com/Nachoide100/Analisis-Idealista-Zaragoza/blob/6be50519cf0e20a23cd5f7ad1b1c064fc422f4ff/visualizations/Captura%20de%20pantalla%202026-02-12%20195646.png)

#### 3️⃣ Página 3: "Investment Hunter" (Cazador de Oportunidades)
**Objetivo:** Herramienta táctica para la toma de decisión final.
* **Tabla de "Chollos":** Listado de activos filtrado automáticamente por el algoritmo `Infravalorado = TRUE`. Incluye formato condicional para resaltar precios atractivos.
* **Medidor de Esfuerzo (Gauge Chart):** KPI visual que calcula los "Años de Renta" necesarios para adquirir la vivienda, con zonas de objetivo (Verde) y riesgo (Rojo) definidas dinámicamente.
* **Filtros Avanzados:** Panel lateral para segmentar por presupuesto máximo, habitaciones y distrito. 

![informe3](https://github.com/Nachoide100/Analisis-Idealista-Zaragoza/blob/6be50519cf0e20a23cd5f7ad1b1c064fc422f4ff/visualizations/Captura%20de%20pantalla%202026-02-12%20195653.png)

#### 4️⃣ Funcionalidad UX: "Neighborhood Deep Dive" (Drill-through)
Se implementó una experiencia de usuario profunda mediante **Drill-through (Obtención de detalles)**.
* **Funcionamiento:** El usuario puede hacer clic en cualquier barrio de los gráficos y luego pulsar el botón de "Ver Detalles de Barrio". 
* **Resultado:** El informe navega a una **página oculta de detalle**, filtrando automáticamente todos los visuales para mostrar exclusivamente la micro-economía de ese barrio (dispersión de precios específica, stock disponible y métricas locales).

![drill](https://github.com/Nachoide100/Analisis-Idealista-Zaragoza/blob/6be50519cf0e20a23cd5f7ad1b1c064fc422f4ff/visualizations/Captura%20de%20pantalla%202026-02-12%20192534.png)

#### Acceso al informe dinámico en Power BI -> [informe](https://drive.google.com/file/d/1HeTp0BWK6H5dl48G5CTR_uzJI9ZmALUW/view?usp=drive_link)

### 💡 Conclusiones del Proyecto
Este desarrollo ha cubierto el ciclo de vida completo del dato (ETL → DWH → BI), destacando por:

✅ **Ingeniería Resiliente (Web Scraping)**
Pivotamos de Selenium a una Ingesta Híbrida (DOM Parsing), logrando sortear sistemas de seguridad avanzados (Datadome) y garantizando la integridad de los datos.

✅ **Data Quality & Enrichment**
Transformamos datos "sucios" en un Dataset Premium al cruzar precios con Renta y Seguridad, permitiendo segmentaciones avanzadas imposibles en portales web tradicionales.

✅ **Arquitectura Profesional**
El uso de PostgreSQL + Star Schema garantiza que el sistema sea escalable y mantenible, soportando futuras cargas de datos masivas.

✅ **Impacto Real en Negocio**
El Dashboard final reduce el "Time-to-Decision" de semanas a minutos. La página "Investment Hunter" ofrece a la inversora una lista de oportunidades matemáticas libres de sesgos emocionales.

---

José Ignacio Rubio

Data Analyst | Business Intelligence Specialist

[[LinkedIn](https://www.linkedin.com/in/jos%C3%A9-ignacio-rubio-194471308/)] | [Portfolio](https://github.com/Nachoide100/Nachoide100.git)

