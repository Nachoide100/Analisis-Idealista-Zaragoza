import os
from bs4 import BeautifulSoup
import pandas as pd

# --- CONFIGURACIÓN ---
# Ruta de la carpeta donde guardaste los HTMLs
# Si la carpeta está en el mismo sitio que este script, usa esto:
CARPETA_HTML = "paginas_web" 

data_list = []

print(f"📂 Buscando archivos en: {CARPETA_HTML}...")

# 1. Obtener lista de archivos .html
try:
    archivos = [f for f in os.listdir(CARPETA_HTML) if f.endswith(".html")]
except FileNotFoundError:
    print(f"❌ Error: No encuentro la carpeta '{CARPETA_HTML}'. Asegúrate de crearla y poner los HTMLs dentro.")
    archivos = []

# 2. Bucle para procesar cada archivo
for nombre_archivo in archivos:
    ruta_completa = os.path.join(CARPETA_HTML, nombre_archivo)
    print(f"📄 Procesando: {nombre_archivo}...")
    
    try:
        # Abrimos el archivo LOCALMENTE (sin internet)
        # errors='ignore' ayuda si hay caracteres raros que no sean UTF-8
        with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
            contenido_html = f.read()
            
        soup = BeautifulSoup(contenido_html, "html.parser")
        
        # Buscar los anuncios (la clase suele ser 'item')
        articles = soup.find_all("article", class_="item")
        
        print(f"   -> Encontrados {len(articles)} anuncios.")

        for article in articles:
            try:
                # --- EXTRACCIÓN (Misma lógica que antes) ---
                
                # Título
                link_tag = article.find("a", class_="item-link")
                titulo = link_tag.text.strip() if link_tag else "N/A"
                
                # Precio
                price_tag = article.find("span", class_="item-price")
                # Limpieza: quitamos puntos y el símbolo €
                precio_texto = price_tag.text.strip().replace(".", "").replace("€", "") if price_tag else "0"
                
                # Habitaciones y Metros
                detalles = article.find_all("span", class_="item-detail")
                habs = 0
                metros = 0
                planta = "N/A"
                
                for det in detalles:
                    txt = det.text.strip()
                    if "hab" in txt:
                        habs = int(txt.split()[0])
                    elif "m²" in txt:
                        metros = int(txt.split()[0].replace(".", ""))
                    elif "planta" in txt or "Bajo" in txt:
                        planta = txt

                # Barrio (Lógica simple: coger lo que hay después de "en")
                barrio = "Zaragoza"
                if " en " in titulo:
                    barrio = titulo.split(" en ")[-1].strip()

                # Solo guardar si tiene precio
                if precio_texto != "0":
                    data_list.append({
                        "Titulo": titulo,
                        "Precio": int(precio_texto),
                        "Habitaciones": habs,
                        "Metros": metros,
                        "Planta": planta,
                        "Barrio": barrio,
                        "Fuente": nombre_archivo # Para saber de qué archivo vino
                    })

            except Exception as e:
                # Si falla un anuncio concreto, lo saltamos y seguimos
                continue
                
    except Exception as e:
        print(f"⚠️ Error leyendo el archivo {nombre_archivo}: {e}")

# --- GUARDADO FINAL ---
if data_list:
    df = pd.DataFrame(data_list)
    print("\n✅ ¡ÉXITO! Datos extraídos correctamente.")
    print(f"📊 Total inmuebles: {len(df)}")
    print(df.head())
    
    # Guardar CSV listo para SQL
    df.to_csv("inmuebles_zaragoza_limpio.csv", index=False, encoding="utf-8-sig")
    print("💾 Archivo guardado: inmuebles_zaragoza_limpio.csv")
else:
    print("\n❌ No se extrajeron datos. Revisa si los HTMLs tienen contenido.")