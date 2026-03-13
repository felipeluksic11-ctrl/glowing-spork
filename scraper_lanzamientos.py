#!/usr/bin/env python3
"""
Scraper de lanzamientos inmobiliarios en México.
3 capas de fuentes: portales directos, RSS de revistas/noticias, búsqueda web.
"""

import csv
import json
import os
import re
import sys
import time
import random
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin, quote_plus

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instalando dependencias...")
    os.system("pip install requests beautifulsoup4")
    import requests
    from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANZAMIENTOS_CSV = os.path.join(BASE_DIR, "lanzamientos.csv")
FUENTES_CSV = os.path.join(BASE_DIR, "fuentes_lanzamientos.csv")

LANZAMIENTOS_HEADERS = [
    "nombre_proyecto", "desarrolladora", "ciudad", "estado_republica", "zona",
    "tipo_desarrollo", "tipo_unidades", "rango_precios", "num_unidades",
    "fecha_entrega_estimada", "etapa", "url_fuente", "portal_fuente",
    "fecha_deteccion", "notas"
]

FUENTES_HEADERS = ["portal", "url_consultada", "fecha_consulta", "proyectos_encontrados", "status"]

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
    "Connection": "keep-alive",
}

ESTADOS_MX = [
    "aguascalientes", "baja california", "baja california sur", "campeche",
    "chiapas", "chihuahua", "cdmx", "ciudad de mexico", "coahuila", "colima",
    "durango", "guanajuato", "guerrero", "hidalgo", "jalisco", "mexico",
    "estado de mexico", "michoacan", "morelos", "nayarit", "nuevo leon",
    "oaxaca", "puebla", "queretaro", "quintana roo", "san luis potosi",
    "sinaloa", "sonora", "tabasco", "tamaulipas", "tlaxcala", "veracruz",
    "yucatan", "zacatecas"
]

CIUDADES_PRINCIPALES = [
    "CDMX", "Guadalajara", "Monterrey", "Mérida", "Cancún",
    "Querétaro", "Puebla", "León", "Tijuana", "Tulum",
    "Playa del Carmen", "San Miguel de Allende"
]

# ─── Utilidades ──────────────────────────────────────────────────────────────


def normalizar(texto):
    if not texto:
        return ""
    import unicodedata
    texto = unicodedata.normalize("NFKD", texto.lower().strip())
    texto = re.sub(r"[\u0300-\u036f]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def cargar_lanzamientos_existentes():
    existentes = set()
    if os.path.exists(LANZAMIENTOS_CSV):
        with open(LANZAMIENTOS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clave = normalizar(row.get("nombre_proyecto", "")) + "|" + normalizar(row.get("ciudad", ""))
                existentes.add(clave)
    return existentes


def proyecto_existe(nombre, ciudad, existentes):
    clave = normalizar(nombre) + "|" + normalizar(ciudad)
    return clave in existentes


def guardar_lanzamiento(proyecto):
    existe = os.path.exists(LANZAMIENTOS_CSV)
    with open(LANZAMIENTOS_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LANZAMIENTOS_HEADERS)
        if not existe:
            writer.writeheader()
        writer.writerow(proyecto)


def guardar_fuente(fuente):
    existe = os.path.exists(FUENTES_CSV)
    with open(FUENTES_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FUENTES_HEADERS)
        if not existe:
            writer.writeheader()
        writer.writerow(fuente)


def delay(min_s=2, max_s=4):
    time.sleep(random.uniform(min_s, max_s))


def fetch_page(url, session=None, timeout=15):
    s = session or requests.Session()
    try:
        resp = s.get(url, headers=HEADERS_HTTP, timeout=timeout)
        resp.raise_for_status()
        return resp.text, resp.status_code
    except requests.RequestException as e:
        code = 0
        if hasattr(e, "response") and e.response is not None:
            code = e.response.status_code
        print(f"  Error al acceder a {url}: {e}")
        return None, code


def detectar_etapa(texto):
    texto = texto.lower()
    if "lanzamiento" in texto:
        return "Lanzamiento"
    if "próximamente" in texto or "proximamente" in texto:
        return "Próximamente"
    if "en construcción" in texto or "en construccion" in texto:
        return "En construcción"
    if "preventa" in texto or "pre-venta" in texto or "pre venta" in texto:
        return "Preventa"
    return "Preventa"


def detectar_tipo(texto):
    texto = texto.lower()
    if any(w in texto for w in ["casa", "casas", "residencia", "residencial"]):
        return "Casas"
    if any(w in texto for w in ["lote", "terreno", "lotes", "terrenos"]):
        return "Lotes"
    if any(w in texto for w in ["oficina", "oficinas", "corporativo"]):
        return "Oficinas"
    if any(w in texto for w in ["local", "comercial", "plaza"]):
        return "Locales comerciales"
    return "Departamentos"


def nuevo_proyecto(nombre, ciudad="", estado="", zona="", desarrolladora="",
                   tipo_desarrollo="Residencial", tipo_unidades="Departamentos",
                   precio="", num_unidades="", fecha_entrega="", etapa="Preventa",
                   url="", portal="", notas=""):
    return {
        "nombre_proyecto": nombre,
        "desarrolladora": desarrolladora,
        "ciudad": ciudad,
        "estado_republica": estado,
        "zona": zona,
        "tipo_desarrollo": tipo_desarrollo,
        "tipo_unidades": tipo_unidades,
        "rango_precios": precio,
        "num_unidades": num_unidades,
        "fecha_entrega_estimada": fecha_entrega,
        "etapa": etapa,
        "url_fuente": url,
        "portal_fuente": portal,
        "fecha_deteccion": datetime.now().strftime("%Y-%m-%d"),
        "notas": notas,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TheRedSearch (scraping autenticado)
# ═══════════════════════════════════════════════════════════════════════════════

REDSEARCH_EMAIL = os.environ.get("REDSEARCH_EMAIL", "fluksic@nativatulum.mx")
REDSEARCH_PASS = os.environ.get("REDSEARCH_PASS", "NativaTulum2026")


def _redsearch_login(session):
    """Autentica en TheRedSearch y retorna True si exitoso."""
    login_url = "https://theredsearch.com/dashboard/?codigo=CU001"
    resp = session.post(login_url, data={
        "login": REDSEARCH_EMAIL,
        "password": REDSEARCH_PASS,
        "Submit": "ACCEDER",
    }, headers=HEADERS_HTTP, timeout=15, allow_redirects=True)
    # Si ya no hay campo password, login exitoso
    return "name=\"password\"" not in resp.text


def _redsearch_parse_cards(soup):
    """Parsea cards de desarrollos (usado en Próximamente y Nuevos por mes)."""
    proyectos = []
    items = soup.select("div.list-result-item")
    for item in items:
        nombre_el = item.select_one(".list-name a") or item.select_one("a.nombre")
        if not nombre_el:
            continue
        nombre = nombre_el.get_text(strip=True)
        if not nombre or len(nombre) < 3:
            continue

        ciudad_el = item.select_one(".list-city")
        ciudad_raw = ciudad_el.get_text(strip=True) if ciudad_el else ""

        # Parsear "Zona, Ciudad" o "Zona Ciudad"
        partes = [p.strip() for p in ciudad_raw.split(",")]
        zona = partes[0] if len(partes) >= 2 else ""
        ciudad = partes[-1].strip() if partes else ""

        etapa_el = item.select_one(".list-tag")
        etapa_txt = etapa_el.get_text(strip=True) if etapa_el else ""
        etapa = "Próximamente" if "PROXIMAMENTE" in etapa_txt.upper() else detectar_etapa(etapa_txt or nombre)

        tipo_el = item.select_one(".list-bed")
        tipo_txt = tipo_el.get_text(strip=True) if tipo_el else ""
        tipo = detectar_tipo(tipo_txt) if tipo_txt else "Departamentos"

        id_el = item.select_one(".list-id a")
        url_det = id_el["href"] if id_el and id_el.get("href") else ""
        if url_det and not url_det.startswith("http"):
            url_det = "https://theredsearch.com" + url_det

        # Mapear ciudad a estado
        _, estado = _extraer_ubicacion(ciudad_raw.lower())

        proyectos.append(nuevo_proyecto(
            nombre=nombre, ciudad=ciudad, estado=estado, zona=zona,
            tipo_unidades=tipo, etapa=etapa,
            url=url_det, portal="TheRedSearch",
            notas=f"Tipo: {tipo_txt}" if tipo_txt else "",
        ))
    return proyectos


def _redsearch_parse_table(soup):
    """Parsea la tabla de Todos los Desarrollos."""
    proyectos = []
    table = soup.select_one("table.misDesarrollos")
    if not table:
        return proyectos

    rows = table.find_all("tr")
    for row in rows[1:]:  # Skip header
        tds = row.find_all("td")
        if len(tds) < 5:
            continue

        # Col 4: INVENTARIO (num unidades) — filtrar unidades individuales
        num_unidades = tds[4].get_text(strip=True)
        try:
            units = int(num_unidades) if num_unidades else 0
        except (ValueError, TypeError):
            units = 0
        if units <= 1:
            continue  # Saltar listings individuales (corretaje)

        # Col 1: NOMBRE (con link)
        nombre_el = tds[1].find("a", href=True)
        if not nombre_el:
            continue
        nombre = nombre_el.get_text(strip=True)
        if not nombre or len(nombre) < 3:
            continue
        url_det = nombre_el["href"]
        if not url_det.startswith("http"):
            url_det = "https://theredsearch.com" + url_det

        # Col 2: DIRECCION (zona + ciudad)
        dir_text = tds[2].get_text(strip=True)
        ciudad, estado = _extraer_ubicacion(dir_text.lower())
        zona = dir_text.replace(ciudad, "").strip() if ciudad else dir_text

        # Col 3: FECHA ENTREGA
        fecha_entrega = tds[3].get_text(strip=True)

        # Col 5: CONTACTO (desarrolladora)
        desarrolladora = tds[5].get_text(strip=True) if len(tds) > 5 else ""

        # Col 6: INFO (link a Drive/Dropbox)
        info_link = ""
        if len(tds) > 6:
            info_a = tds[6].find("a", href=True)
            if info_a:
                info_link = info_a["href"]

        proyectos.append(nuevo_proyecto(
            nombre=nombre, ciudad=ciudad, estado=estado, zona=zona,
            desarrolladora=desarrolladora,
            num_unidades=num_unidades,
            fecha_entrega=fecha_entrega,
            url=url_det, portal="TheRedSearch",
            notas=f"Info: {info_link}" if info_link else "",
        ))
    return proyectos


def scrape_redsearch(session):
    """Scraping autenticado de TheRedSearch — Península de Yucatán."""
    print("\n  TheRedSearch: autenticando...")

    if not _redsearch_login(session):
        print("    Error: no se pudo autenticar en TheRedSearch")
        guardar_fuente({
            "portal": "TheRedSearch", "url_consultada": "https://theredsearch.com/dashboard/",
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
            "proyectos_encontrados": 0, "status": "error_login"
        })
        return []

    print("    Login exitoso")
    todos = []

    # 1. Próximamente (CU510)
    print("    Próximamente...")
    html, status = fetch_page("https://theredsearch.com/processing/?codigo=CU510", session)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        prox = _redsearch_parse_cards(soup)
        for p in prox:
            p["etapa"] = "Próximamente"
        todos.extend(prox)
        print(f"      {len(prox)} desarrollos próximamente")
    delay(1, 2)

    # 2. Nuevos del mes actual y anterior
    now = datetime.now()
    for delta in [0, -1]:
        month = now.month + delta
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        code = f"M{year}{month:02d}"
        label = f"{year}-{month:02d}"
        print(f"    Nuevos desarrollos {label}...")
        html, status = fetch_page(f"https://theredsearch.com/processing/?codigo={code}", session)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            nuevos = _redsearch_parse_cards(soup)
            todos.extend(nuevos)
            print(f"      {len(nuevos)} desarrollos nuevos en {label}")
        delay(1, 2)

    # 3. Todos los Desarrollos (tabla completa)
    print("    Todos los desarrollos (tabla)...")
    html, status = fetch_page("https://theredsearch.com/processing/?codigo=CU507", session, timeout=30)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        tabla = _redsearch_parse_table(soup)
        todos.extend(tabla)
        print(f"      {len(tabla)} desarrollos en tabla total")

    guardar_fuente({
        "portal": "TheRedSearch",
        "url_consultada": "https://theredsearch.com/processing/",
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
        "proyectos_encontrados": len(todos),
        "status": "ok" if todos else "ok_0_results"
    })

    return todos


# ═══════════════════════════════════════════════════════════════════════════════
# CAPA 1: Portales directos (los que NO bloquean)
# ═══════════════════════════════════════════════════════════════════════════════


def scrape_portales_via_busqueda(session):
    """Capa 1: Portales SPA (La Haus, Behome, MTY Skyline) via DuckDuckGo.
    Estos portales son SPAs (React/Next.js) y no sirven HTML estático,
    así que usamos búsqueda web con site: para extraer sus listados.
    Con el skill de Claude (/detector-lanzamientos) se usa WebFetch que sí renderiza JS.
    """
    queries_portales = [
        ('site:lahaus.mx preventa desarrollo nuevo departamentos', "La Haus"),
        ('site:lahaus.mx preventa guadalajara monterrey cdmx', "La Haus"),
        ('site:lahaus.mx preventa cancun tulum merida queretaro', "La Haus"),
        ('site:behome.mx desarrollo preventa riviera maya cancun tulum', "Behome"),
        ('site:monterreyskyline.com desarrollo preventa monterrey', "Monterrey Skyline"),
    ]

    todos_proyectos = []
    for query, portal in queries_portales:
        print(f"  {portal} (búsqueda): {query[:50]}...")
        resultados = busqueda_duckduckgo(session, query)

        proyectos = []
        for r in resultados:
            titulo = r["titulo"]
            url_r = r["url"]
            snippet = r["snippet"]
            texto = f"{titulo} {snippet}".lower()

            es_relevante = any(kw in texto for kw in [
                "preventa", "desarrollo", "departamento", "torre",
                "residencial", "proyecto", "lanzamiento"
            ])
            if not es_relevante:
                continue

            nombre = _extraer_nombre_proyecto(titulo) or titulo[:60]
            ciudad, estado = _extraer_ubicacion(texto)
            etapa = detectar_etapa(texto)
            tipo = detectar_tipo(texto)
            precio = _extraer_precio(texto)

            proyectos.append(nuevo_proyecto(
                nombre=nombre, ciudad=ciudad, estado=estado,
                tipo_unidades=tipo, precio=precio, etapa=etapa,
                url=url_r, portal=portal,
                notas=f"Vía búsqueda site:{portal.lower().replace(' ', '')}"
            ))

        guardar_fuente({
            "portal": portal, "url_consultada": f"duckduckgo.com: {query[:60]}",
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
            "proyectos_encontrados": len(proyectos), "status": "ok"
        })
        print(f"    {len(proyectos)} resultados relevantes")
        todos_proyectos.extend(proyectos)
        delay(3, 5)

    return todos_proyectos


# ═══════════════════════════════════════════════════════════════════════════════
# CAPA 2: RSS feeds de revistas y noticias
# ═══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS = [
    {
        "portal": "Centro Urbano",
        "url": "https://centrourbano.com/feed/",
        "tipo": "Noticias",
    },
    {
        "portal": "Inmobiliare Magazine",
        "url": "https://www.inmobiliare.com/feed/",
        "tipo": "Revista",
    },
]

# Keywords para filtrar artículos relevantes sobre lanzamientos
KEYWORDS_LANZAMIENTO = [
    "nuevo desarrollo", "nuevo proyecto", "preventa", "pre-venta",
    "lanzamiento", "lanza", "inauguran", "inauguración", "anuncia",
    "inicia construcción", "inicia construccion", "torre", "torres",
    "residencial", "departamentos", "complejo", "desarrollo inmobiliario",
    "vivienda nueva", "proyecto inmobiliario", "inversión inmobiliaria",
]


def scrape_rss_feeds(session):
    """Parsea feeds RSS de revistas y noticias inmobiliarias."""
    todos_proyectos = []

    for feed_info in RSS_FEEDS:
        portal = feed_info["portal"]
        url = feed_info["url"]
        print(f"\n  RSS: {portal}...")

        html, status = fetch_page(url, session, timeout=20)
        if not html:
            guardar_fuente({
                "portal": portal, "url_consultada": url,
                "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
                "proyectos_encontrados": 0, "status": f"error_{status}"
            })
            continue

        proyectos = []
        try:
            root = ET.fromstring(html)
            # Buscar items (RSS 2.0)
            ns = {"content": "http://purl.org/rss/1.0/modules/content/",
                  "dc": "http://purl.org/dc/elements/1.1/"}
            items = root.findall(".//item")

            for item in items:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                description = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")
                content = item.findtext("content:encoded", "", ns)
                categories = [c.text for c in item.findall("category") if c.text]

                # Combinar todo el texto para buscar keywords
                texto_completo = f"{title} {description} {content}".lower()

                # Filtrar: solo artículos relacionados con lanzamientos inmobiliarios
                es_relevante = any(kw in texto_completo for kw in KEYWORDS_LANZAMIENTO)
                if not es_relevante:
                    continue

                # Intentar extraer nombre de proyecto del título
                nombre = _extraer_nombre_proyecto(title)
                if not nombre:
                    nombre = title[:80]  # Usar título como nombre

                # Intentar extraer ciudad/estado del contenido
                ciudad, estado = _extraer_ubicacion(texto_completo)

                etapa = detectar_etapa(texto_completo)
                tipo = detectar_tipo(texto_completo)

                # Extraer precio si aparece
                precio = _extraer_precio(texto_completo)

                proyectos.append(nuevo_proyecto(
                    nombre=nombre, ciudad=ciudad, estado=estado,
                    tipo_unidades=tipo, precio=precio, etapa=etapa,
                    url=link, portal=portal,
                    notas=f"Fuente: {portal} | Categorías: {', '.join(categories[:3])}"
                ))

        except ET.ParseError as e:
            print(f"    Error parseando RSS: {e}")
            guardar_fuente({
                "portal": portal, "url_consultada": url,
                "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
                "proyectos_encontrados": 0, "status": f"error_parse: {e}"
            })
            continue

        guardar_fuente({
            "portal": portal, "url_consultada": url,
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
            "proyectos_encontrados": len(proyectos), "status": "ok"
        })
        print(f"    {portal}: {len(proyectos)} artículos relevantes")
        todos_proyectos.extend(proyectos)
        delay(1, 2)

    return todos_proyectos


def _extraer_nombre_proyecto(titulo):
    """Intenta extraer el nombre del proyecto de un título de artículo."""
    # Buscar patrones comunes: "Proyecto X", "Desarrollo X", nombres entre comillas
    patterns = [
        r'"([^"]+)"',  # Entre comillas
        r"'([^']+)'",  # Entre comillas simples
        r"«([^»]+)»",  # Entre comillas latinas
        r"(?:proyecto|desarrollo|torre|residencial|complejo)\s+([A-ZÁ-Ú][a-záéíóúñ]+(?:\s+[A-ZÁ-Ú][a-záéíóúñ]+)*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, titulo, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extraer_ubicacion(texto):
    """Extrae ciudad y estado del texto de un artículo."""
    ciudades_estado = {
        "cdmx": ("CDMX", "CDMX"),
        "ciudad de méxico": ("CDMX", "CDMX"),
        "ciudad de mexico": ("CDMX", "CDMX"),
        "guadalajara": ("Guadalajara", "Jalisco"),
        "monterrey": ("Monterrey", "Nuevo León"),
        "mérida": ("Mérida", "Yucatán"),
        "merida": ("Mérida", "Yucatán"),
        "cancún": ("Cancún", "Quintana Roo"),
        "cancun": ("Cancún", "Quintana Roo"),
        "tulum": ("Tulum", "Quintana Roo"),
        "playa del carmen": ("Playa del Carmen", "Quintana Roo"),
        "querétaro": ("Querétaro", "Querétaro"),
        "queretaro": ("Querétaro", "Querétaro"),
        "puebla": ("Puebla", "Puebla"),
        "león": ("León", "Guanajuato"),
        "leon": ("León", "Guanajuato"),
        "tijuana": ("Tijuana", "Baja California"),
        "san miguel de allende": ("San Miguel de Allende", "Guanajuato"),
        "los cabos": ("Los Cabos", "Baja California Sur"),
        "vallarta": ("Puerto Vallarta", "Jalisco"),
        "riviera maya": ("Riviera Maya", "Quintana Roo"),
        # Península de Yucatán (TheRedSearch)
        "puerto aventuras": ("Puerto Aventuras", "Quintana Roo"),
        "puerto morelos": ("Puerto Morelos", "Quintana Roo"),
        "akumal": ("Akumal", "Quintana Roo"),
        "cozumel": ("Cozumel", "Quintana Roo"),
        "bacalar": ("Bacalar", "Quintana Roo"),
        "costa maya": ("Costa Maya", "Quintana Roo"),
        "mahahual": ("Mahahual", "Quintana Roo"),
        "isla mujeres": ("Isla Mujeres", "Quintana Roo"),
        "holbox": ("Holbox", "Quintana Roo"),
        "costa yucateca": ("Costa Yucateca", "Yucatán"),
        "telchac": ("Telchac Puerto", "Yucatán"),
        "chicxulub": ("Chicxulub", "Yucatán"),
        "chelem": ("Chelem", "Yucatán"),
        "sisal": ("Sisal", "Yucatán"),
        "san crisanto": ("San Crisanto", "Yucatán"),
        "yucalpeten": ("Yucalpetén", "Yucatán"),
        "valladolid": ("Valladolid", "Yucatán"),
        "progreso": ("Progreso", "Yucatán"),
        "campeche": ("Campeche", "Campeche"),
        "yucatan": ("Yucatán", "Yucatán"),
    }
    texto_lower = texto.lower()
    for key, (ciudad, estado) in ciudades_estado.items():
        if key in texto_lower:
            return ciudad, estado
    return "", ""


def _extraer_precio(texto):
    """Extrae precio del texto si aparece."""
    patterns = [
        r"\$[\d,]+(?:\.\d+)?\s*(?:mdp|millones|mxn|pesos)",
        r"desde\s+\$[\d,]+",
        r"\$[\d,]{6,}",
    ]
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# CAPA 3: Búsqueda web (DuckDuckGo) para portales bloqueados
# ═══════════════════════════════════════════════════════════════════════════════

SEARCH_QUERIES = [
    # Búsquedas por portal bloqueado (fallback si scrape directo falla)
    ('site:lamudi.com.mx preventa nuevo desarrollo 2026', "Lamudi"),
    ('site:casasyterrenos.com preventa desarrollo', "Casas y Terrenos"),
    # Búsquedas generales
    ('nuevo desarrollo inmobiliario preventa México 2026', "Google News MX"),
    ('lanzamiento proyecto inmobiliario CDMX Monterrey Guadalajara 2026', "Google News MX"),
    ('preventa departamentos torre México 2026', "Google News MX"),
]


def scrape_inmuebles24_desarrollos(session):
    """Inmuebles24 - scraping directo de https://www.inmuebles24.com/desarrollos.html"""
    portal = "Inmuebles24"
    url = "https://www.inmuebles24.com/desarrollos.html"
    proyectos = []

    print(f"  Inmuebles24: {url}")
    html, status = fetch_page(url, session, timeout=20)

    if not html:
        print(f"    Bloqueado ({status}), usando DuckDuckGo como fallback...")
        # Fallback a búsqueda
        resultados = busqueda_duckduckgo(session, "site:inmuebles24.com/desarrollos preventa nuevo 2026")
        for r in resultados:
            texto = f"{r['titulo']} {r['snippet']}".lower()
            if not any(kw in texto for kw in ["preventa", "desarrollo", "departamento", "torre"]):
                continue
            nombre = _extraer_nombre_proyecto(r["titulo"]) or r["titulo"][:60]
            ciudad, estado = _extraer_ubicacion(texto)
            proyectos.append(nuevo_proyecto(
                nombre=nombre, ciudad=ciudad, estado=estado,
                tipo_unidades=detectar_tipo(texto), precio=_extraer_precio(texto),
                etapa=detectar_etapa(texto), url=r["url"], portal=portal,
                notas="Vía búsqueda (scraping bloqueado)"
            ))
        guardar_fuente({
            "portal": portal, "url_consultada": url,
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
            "proyectos_encontrados": len(proyectos), "status": f"fallback_busqueda_{status}"
        })
        return proyectos

    soup = BeautifulSoup(html, "html.parser")

    # Inmuebles24 desarrollos page selectors
    listings = soup.select(
        "div.posting-card, div[data-qa='posting'], article[class*='posting'], "
        "div[class*='CardContainer'], div[class*='development-card'], "
        "a[data-qa='posting DEVELOPMENT']"
    )
    if not listings:
        listings = soup.select("div[class*='card'], div[class*='listing'], article")

    for listing in listings:
        try:
            titulo_el = listing.select_one(
                "h2, h3, [data-qa='posting-title'], [class*='title'], "
                "[class*='PostingCardTitle'], a[class*='posting']"
            )
            nombre = titulo_el.get_text(strip=True) if titulo_el else None
            if not nombre or len(nombre) < 3:
                continue

            link_el = listing if listing.name == "a" else listing.select_one("a[href]")
            url_det = urljoin(url, link_el["href"]) if link_el and link_el.get("href") else url

            ubicacion_el = listing.select_one(
                "[class*='location'], [class*='address'], "
                "[data-qa='posting-location'], [class*='PostingCardLocation']"
            )
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""

            precio_el = listing.select_one("[class*='price'], [data-qa='posting-price']")
            precio = precio_el.get_text(strip=True) if precio_el else ""

            texto_completo = listing.get_text(separator=" ", strip=True)
            etapa = detectar_etapa(texto_completo)
            tipo = detectar_tipo(texto_completo)

            partes_ub = [p.strip() for p in ubicacion.split(",")]
            ciudad = partes_ub[-2] if len(partes_ub) >= 2 else (partes_ub[0] if partes_ub else "")
            estado_rep = partes_ub[-1] if len(partes_ub) >= 2 else ""
            zona = partes_ub[0] if len(partes_ub) >= 3 else ""

            proyectos.append(nuevo_proyecto(
                nombre=nombre, ciudad=ciudad.strip(), estado=estado_rep.strip(),
                zona=zona.strip(), tipo_unidades=tipo, precio=precio,
                etapa=etapa, url=url_det, portal=portal
            ))
        except Exception as e:
            print(f"    Error en listing: {e}")
            continue

    guardar_fuente({
        "portal": portal, "url_consultada": url,
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
        "proyectos_encontrados": len(proyectos), "status": "ok" if proyectos else "ok_0_results"
    })
    print(f"    Inmuebles24: {len(proyectos)} proyectos")
    return proyectos


def busqueda_duckduckgo(session, query, max_results=10):
    """Busca en DuckDuckGo HTML (no requiere API key)."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {**HEADERS_HTTP, "Referer": "https://duckduckgo.com/"}

    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        resultados = []
        for result in soup.select("div.result, div.web-result")[:max_results]:
            titulo_el = result.select_one("a.result__a, h2 a")
            snippet_el = result.select_one("a.result__snippet, .result__snippet")

            if not titulo_el:
                continue

            titulo = titulo_el.get_text(strip=True)
            link = titulo_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # Limpiar URL de DuckDuckGo redirect
            if "uddg=" in link:
                match = re.search(r"uddg=([^&]+)", link)
                if match:
                    from urllib.parse import unquote
                    link = unquote(match.group(1))

            resultados.append({
                "titulo": titulo,
                "url": link,
                "snippet": snippet,
            })

        return resultados
    except Exception as e:
        print(f"    Error DuckDuckGo: {e}")
        return []


def scrape_busqueda_web(session):
    """Usa búsqueda web para encontrar lanzamientos en portales bloqueados."""
    todos_proyectos = []

    for query, portal in SEARCH_QUERIES:
        print(f"\n  Buscando: {query[:50]}...")
        resultados = busqueda_duckduckgo(session, query)

        if not resultados:
            guardar_fuente({
                "portal": portal, "url_consultada": f"duckduckgo.com: {query[:60]}",
                "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
                "proyectos_encontrados": 0, "status": "ok_sin_resultados"
            })
            delay(3, 6)
            continue

        proyectos = []
        for r in resultados:
            titulo = r["titulo"]
            url_r = r["url"]
            snippet = r["snippet"]
            texto = f"{titulo} {snippet}"

            # Filtrar solo resultados relevantes
            texto_lower = texto.lower()
            es_relevante = any(kw in texto_lower for kw in [
                "preventa", "desarrollo", "lanzamiento", "nuevo proyecto",
                "torre", "residencial", "departamentos", "inmobiliario"
            ])
            if not es_relevante:
                continue

            nombre = _extraer_nombre_proyecto(titulo) or titulo[:60]
            ciudad, estado = _extraer_ubicacion(texto_lower)
            etapa = detectar_etapa(texto_lower)
            tipo = detectar_tipo(texto_lower)
            precio = _extraer_precio(texto_lower)

            proyectos.append(nuevo_proyecto(
                nombre=nombre, ciudad=ciudad, estado=estado,
                tipo_unidades=tipo, precio=precio, etapa=etapa,
                url=url_r, portal=portal,
                notas=f"Detectado vía búsqueda web: {snippet[:100]}"
            ))

        guardar_fuente({
            "portal": portal, "url_consultada": f"duckduckgo.com: {query[:60]}",
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d"),
            "proyectos_encontrados": len(proyectos), "status": "ok"
        })
        print(f"    {len(proyectos)} resultados relevantes")
        todos_proyectos.extend(proyectos)
        delay(3, 6)  # Más delay para no ser bloqueados por DDG

    return todos_proyectos


# ═══════════════════════════════════════════════════════════════════════════════
# Orquestador principal
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("DETECTOR DE LANZAMIENTOS INMOBILIARIOS - MÉXICO")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Estrategia: 3 capas (portales + RSS + búsqueda web)")
    print("=" * 60)

    # Parsear argumentos
    filtro_capa = None  # "portales", "rss", "busqueda", "redsearch"
    args = [a.strip() for a in sys.argv[1:]]
    for arg in args:
        arg_lower = arg.lower()
        if arg_lower in ("portales", "rss", "revistas", "busqueda", "noticias", "redsearch"):
            filtro_capa = arg_lower

    existentes = cargar_lanzamientos_existentes()
    print(f"\nProyectos previamente registrados: {len(existentes)}")

    session = requests.Session()
    todos_proyectos = []

    # --- CAPA 1: Portales ---
    if not filtro_capa or filtro_capa == "portales":
        print(f"\n{'─'*60}")
        print("CAPA 1: Portales (Inmuebles24 directo + SPAs via búsqueda)")
        print(f"{'─'*60}")

        # Inmuebles24 - scraping directo de /desarrollos.html
        try:
            proyectos_i24 = scrape_inmuebles24_desarrollos(session)
            todos_proyectos.extend(proyectos_i24)
        except Exception as e:
            print(f"  Error Inmuebles24: {e}")
        delay(2, 4)

        # SPAs via búsqueda (La Haus, Behome, MTY Skyline)
        try:
            proyectos = scrape_portales_via_busqueda(session)
            todos_proyectos.extend(proyectos)
        except Exception as e:
            print(f"  Error búsqueda portales: {e}")

    # --- TheRedSearch (autenticado) ---
    if not filtro_capa or filtro_capa == "redsearch":
        print(f"\n{'─'*60}")
        print("TheRedSearch (scraping autenticado - Península de Yucatán)")
        print(f"{'─'*60}")

        try:
            proyectos_rs = scrape_redsearch(session)
            todos_proyectos.extend(proyectos_rs)
        except Exception as e:
            print(f"  Error TheRedSearch: {e}")

    # --- CAPA 2: RSS feeds ---
    if not filtro_capa or filtro_capa in ("rss", "revistas"):
        print(f"\n{'─'*60}")
        print("CAPA 2: RSS feeds (Centro Urbano, Inmobiliare)")
        print(f"{'─'*60}")

        try:
            proyectos_rss = scrape_rss_feeds(session)
            todos_proyectos.extend(proyectos_rss)
        except Exception as e:
            print(f"  Error en RSS: {e}")

    # --- CAPA 3: Búsqueda web ---
    if not filtro_capa or filtro_capa in ("busqueda", "noticias"):
        print(f"\n{'─'*60}")
        print("CAPA 3: Búsqueda web (DuckDuckGo - portales bloqueados)")
        print(f"{'─'*60}")

        try:
            proyectos_busq = scrape_busqueda_web(session)
            todos_proyectos.extend(proyectos_busq)
        except Exception as e:
            print(f"  Error en búsqueda: {e}")

    # --- Deduplicar y guardar ---
    nuevos = 0
    duplicados = 0
    for proyecto in todos_proyectos:
        nombre = proyecto.get("nombre_proyecto", "")
        ciudad = proyecto.get("ciudad", "")
        if not nombre or len(nombre) < 3:
            continue
        if proyecto_existe(nombre, ciudad, existentes):
            duplicados += 1
            continue
        guardar_lanzamiento(proyecto)
        clave = normalizar(nombre) + "|" + normalizar(ciudad)
        existentes.add(clave)
        nuevos += 1

    # --- Resumen ---
    print(f"\n{'='*60}")
    print("RESUMEN DE EJECUCIÓN")
    print(f"{'='*60}")
    print(f"Total proyectos encontrados: {len(todos_proyectos)}")
    print(f"Proyectos nuevos registrados: {nuevos}")
    print(f"Proyectos duplicados omitidos: {duplicados}")

    if todos_proyectos:
        por_estado = {}
        por_etapa = {}
        por_ciudad = {}
        por_portal = {}
        for p in todos_proyectos:
            est = p.get("estado_republica") or "Sin estado"
            por_estado[est] = por_estado.get(est, 0) + 1
            et = p.get("etapa") or "Sin etapa"
            por_etapa[et] = por_etapa.get(et, 0) + 1
            c = p.get("ciudad") or "Sin ciudad"
            por_ciudad[c] = por_ciudad.get(c, 0) + 1
            pt = p.get("portal_fuente") or "Desconocido"
            por_portal[pt] = por_portal.get(pt, 0) + 1

        print(f"\nPor estado:")
        for k, v in sorted(por_estado.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

        print(f"\nPor etapa:")
        for k, v in sorted(por_etapa.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

        print(f"\nTop ciudades:")
        for k, v in sorted(por_ciudad.items(), key=lambda x: -x[1])[:10]:
            print(f"  {k}: {v}")

        print(f"\nPor fuente:")
        for k, v in sorted(por_portal.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

    print(f"\nArchivos:")
    print(f"  - {LANZAMIENTOS_CSV}")
    print(f"  - {FUENTES_CSV}")
    print(f"\nDetección automática: /loop 1d /detector-lanzamientos")


if __name__ == "__main__":
    main()
