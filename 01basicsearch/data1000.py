import os
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ==================================================
# CONFIGURACIÓN
# ==================================================
CARPETA_DESTINO = "libros_gutenberg_es"
MAX_LIBROS = 1000  # Descargar exactamente 1000 libros
URL_BASE = "https://www.gutenberg.org"
URL_CATALOGO = "https://www.gutenberg.org/browse/languages/es"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Crear carpeta si no existe
os.makedirs(CARPETA_DESTINO, exist_ok=True)

# ==================================================
# FUNCIONES AUXILIARES
# ==================================================
def limpiar_nombre_archivo(nombre):
    """Limpia el nombre del archivo eliminando caracteres inválidos"""
    # Reemplazar caracteres inválidos en Windows
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    # Limitar longitud del nombre (200 chars es seguro)
    if len(nombre) > 200:
        nombre = nombre[:200]
    # Eliminar espacios al inicio/final
    nombre = nombre.strip()
    # Si queda vacío, usar nombre por defecto
    if not nombre:
        nombre = "libro_sin_titulo"
    return nombre

def obtener_titulo_y_urls_descarga(url_libro):
    """
    Obtiene el título y las URLs de descarga (UTF-8 y normal)
    desde la página del libro
    """
    try:
        response = requests.get(url_libro, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # === OBTENER TÍTULO ===
        titulo = None
        # Buscar en meta tag
        meta_title = soup.find('meta', {'name': 'title'})
        if meta_title and meta_title.get('content'):
            titulo = meta_title['content']
        else:
            # Buscar en el elemento title
            title_tag = soup.find('title')
            if title_tag:
                titulo = title_tag.text
                # Limpiar "Title" y "by Author" que añade Gutenberg
                titulo = re.sub(r'\s*\|?\s*(Project Gutenberg|Free ebook|by.*)$', '', titulo, flags=re.I)
                titulo = titulo.strip()
        
        # Si no hay título, usar el ID
        if not titulo:
            libro_id = url_libro.rstrip('/').split('/')[-1]
            titulo = f"Libro_{libro_id}"
        
        titulo = limpiar_nombre_archivo(titulo)
        
        # === OBTENER URLS DE DESCARGA ===
        urls_descarga = []
        
        # Buscar enlaces de descarga de texto
        for link in soup.find_all('a', href=True):
            href = link['href']
            texto_link = link.text.lower()
            
            # Buscar archivos .txt
            if href.endswith('.txt'):
                url_completa = urljoin(URL_BASE, href)
                # Priorizar UTF-8
                if 'utf-8' in href.lower() or 'utf8' in href.lower():
                    urls_descarga.insert(0, url_completa)  # Priorizar UTF-8
                else:
                    urls_descarga.append(url_completa)
            
            # Buscar enlaces con texto "Plain Text"
            elif 'plain text' in texto_link and 'utf' in texto_link:
                url_completa = urljoin(URL_BASE, href)
                urls_descarga.insert(0, url_completa)
            elif 'plain text' in texto_link:
                url_completa = urljoin(URL_BASE, href)
                urls_descarga.append(url_completa)
        
        return titulo, urls_descarga
        
    except Exception as e:
        print(f"  Error al procesar {url_libro}: {e}")
        return None, []

def obtener_lista_completa_libros():
    """
    Obtiene una lista completa de URLs de libros de todas las páginas del catálogo
    hasta alcanzar MAX_LIBROS o no haber más páginas
    """
    todas_urls = []
    pagina_actual = 1
    
    print(f"Buscando {MAX_LIBROS} libros en español...")
    
    while len(todas_urls) < MAX_LIBROS:
        # Construir URL de paginación (si existe)
        if pagina_actual == 1:
            url_pagina = URL_CATALOGO
        else:
            url_pagina = f"{URL_CATALOGO}/{pagina_actual}"
        
        try:
            print(f"  Explorando página {pagina_actual}...")
            response = requests.get(url_pagina, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                print(f"  No hay más páginas (código {response.status_code})")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar enlaces a libros
            urls_pagina = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Patrón para URLs de libros: /ebooks/NUMERO
                if '/ebooks/' in href:
                    match = re.search(r'/ebooks/(\d+)', href)
                    if match:
                        url_completa = urljoin(URL_BASE, href)
                        if url_completa not in todas_urls and url_completa not in urls_pagina:
                            urls_pagina.append(url_completa)
            
            if not urls_pagina:
                print("  No se encontraron más libros en esta página")
                break
            
            todas_urls.extend(urls_pagina)
            print(f"  Encontrados {len(urls_pagina)} libros en esta página. Acumulado: {len(todas_urls)}")
            
            pagina_actual += 1
            
            # Pequeña pausa entre páginas
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error al obtener página {pagina_actual}: {e}")
            break
    
    # Limitar a MAX_LIBROS
    return todas_urls[:MAX_LIBROS]

def descargar_libro(url_descarga, ruta_completa):
    """Descarga el libro y lo guarda en la ruta especificada"""
    try:
        response = requests.get(url_descarga, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Intentar detectar encoding
        if 'utf-8' in response.headers.get('content-type', '').lower():
            encoding = 'utf-8'
        else:
            encoding = 'utf-8'  # Por defecto UTF-8
            
        response.encoding = encoding
        
        with open(ruta_completa, 'w', encoding='utf-8', errors='replace') as f:
            f.write(response.text)
        return True
    except Exception as e:
        print(f"  Error de descarga: {e}")
        return False

# ==================================================
# PROGRAMA PRINCIPAL
# ==================================================
def main():
    print("=" * 60)
    print("DESCARGA DE 1000 LIBROS DE GUTENBERG (ESPAÑOL)")
    print("=" * 60)
    print(f"📁 Carpeta destino: {CARPETA_DESTINO}")
    print(f"📚 Libros a descargar: {MAX_LIBROS}")
    print(f"🌐 Catálogo: {URL_CATALOGO}")
    print("=" * 60)
    print()
    
    # Paso 1: Obtener URLs de los libros
    urls_libros = obtener_lista_completa_libros()
    
    if not urls_libros:
        print("❌ No se encontraron libros. Verifica:")
        print("   - Tu conexión a internet")
        print("   - Que la página de Gutenberg esté accesible")
        print("   - Que el catálogo en español tenga libros disponibles")
        return
    
    print(f"\n✅ Encontrados {len(urls_libros)} libros en total")
    
    if len(urls_libros) < MAX_LIBROS:
        print(f"⚠️  Solo hay {len(urls_libros)} libros disponibles en el catálogo español.")
        print(f"   Se descargarán todos los disponibles.\n")
    else:
        print(f"✅ Se descargarán exactamente {MAX_LIBROS} libros.\n")
    
    # Paso 2: Descargar cada libro
    descargados = 0
    fallidos = 0
    libros_omitidos = 0
    
    for i, url_libro in enumerate(urls_libros, 1):
        # Mostrar progreso
        print(f"\n[{i}/{len(urls_libros)}] Procesando...")
        
        # Obtener título y URLs de descarga
        titulo, urls_descarga = obtener_titulo_y_urls_descarga(url_libro)
        
        if not titulo or not urls_descarga:
            print(f"  ⚠️  No se pudo obtener información del libro. Omitiendo.")
            fallidos += 1
            continue
        
        # Construir nombre de archivo seguro
        nombre_archivo = f"{titulo}.txt"
        ruta_local = os.path.join(CARPETA_DESTINO, nombre_archivo)
        
        # Verificar si ya existe
        if os.path.exists(ruta_local):
            print(f"  📄 {nombre_archivo}")
            print(f"  ⏭️  Ya existe. Omitiendo.")
            libros_omitidos += 1
            continue
        
        # Intentar descargar con cada URL disponible
        descarga_exitosa = False
        for url_descarga in urls_descarga:
            print(f"  📥 Intentando descargar: {titulo}")
            print(f"     🔗 {url_descarga[:80]}...")
            
            if descargar_libro(url_descarga, ruta_local):
                print(f"  ✅ DESCARGADO: {nombre_archivo}")
                descargados += 1
                descarga_exitosa = True
                break
            else:
                print(f"  ❌ Falló con esta URL")
                continue
        
        if not descarga_exitosa:
            print(f"  ❌ No se pudo descargar {titulo}")
            fallidos += 1
        
        # Pausa entre descargas para no sobrecargar el servidor
        time.sleep(1)
        
        # Verificar si ya alcanzamos la meta
        if descargados >= MAX_LIBROS:
            print(f"\n🎉 ¡Meta alcanzada! Descargados {descargados} libros.")
            break
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE DESCARGA")
    print("=" * 60)
    print(f"📚 Total libros encontrados: {len(urls_libros)}")
    print(f"✅ Descargados exitosamente: {descargados}")
    print(f"⚠️  Omitidos (ya existían): {libros_omitidos}")
    print(f"❌ Fallidos: {fallidos}")
    print(f"📁 Ubicación: {os.path.abspath(CARPETA_DESTINO)}")
    print("=" * 60)
    
    # Listar algunos archivos descargados como muestra
    if descargados > 0:
        print("\n📖 Ejemplos de libros descargados:")
        archivos = os.listdir(CARPETA_DESTINO)
        for archivo in archivos[:10]:
            print(f"   • {archivo}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Descarga interrumpida por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        print("   Revisa tu conexión a internet y vuelve a intentarlo.")