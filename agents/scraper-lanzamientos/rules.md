# Scraper Lanzamientos — Rules

## 1. Rate Limits y Delays

- **Delay entre requests:** espera aleatoria entre 2 y 5 segundos entre cada request al mismo dominio.
- **Delay entre dominios distintos:** mínimo 0.5 segundos.
- Implementar el delay con `time.sleep(random.uniform(min, max))`, no con valores fijos.
- Si el servidor responde con HTTP 429 (Too Many Requests): esperar 60 segundos y reintentar.
- Si el servidor responde con HTTP 503: esperar 30 segundos y reintentar. Máximo 3 reintentos.
- Si el servidor responde con HTTP 403: registrar como `status: error` en fuentes_lanzamientos.csv y no reintentar en la misma ejecución.

## 2. Rotación de User-Agent

Usar un pool de User-Agents reales y rotarlos por request:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]
```

Seleccionar aleatoriamente por request: `random.choice(USER_AGENTS)`.

## 3. Headers del CSV

**lanzamientos.csv** (en este orden exacto):
```
id,nombre_desarrollo,desarrollador,ciudad,estado,tipo_propiedad,precio_desde,moneda,fecha_deteccion,fecha_publicacion,fuente_capa,fuente_nombre,url_fuente,status_verificacion
```

**fuentes_lanzamientos.csv** (en este orden exacto):
```
fuente_nombre,fuente_url,capa,ultimo_scraping,status,n_registros_ultimo,n_registros_total,error_mensaje
```

Nunca modificar el orden de los headers. Nuevos campos se agregan al final.

## 4. Tracking de Status por Fuente

Cada fuente en `fuentes_lanzamientos.csv` debe tener uno de estos estados:
- `ok`: scraping exitoso, al menos 1 resultado obtenido.
- `warning`: scraping exitoso pero 0 resultados (puede ser normal fuera de temporada de lanzamientos).
- `error`: scraping falló por error HTTP, timeout, o parsing error.

Actualizar `fuentes_lanzamientos.csv` al finalizar el scraping de cada fuente, no al final de la ejecución completa.

## 5. Cobertura de Estados Mexicanos

El agente debe cubrir los 32 estados sin excepción. Lista completa:

```
Aguascalientes, Baja California, Baja California Sur, Campeche, Chiapas,
Chihuahua, Coahuila, Colima, Ciudad de México, Durango, Estado de México,
Guanajuato, Guerrero, Hidalgo, Jalisco, Michoacán, Morelos, Nayarit,
Nuevo León, Oaxaca, Puebla, Querétaro, Quintana Roo, San Luis Potosí,
Sinaloa, Sonora, Tabasco, Tamaulipas, Tlaxcala, Veracruz, Yucatán, Zacatecas
```

Para la Capa 3 (SERP), priorizar estados de Zona 1 y Zona 2 en cada ejecución. Los demás estados se procesan en rotación: la ejecución registra en `fuentes_lanzamientos.csv` qué estados fueron cubiertos en el último run.

## 6. Deduplicación

- El `id` es el hash MD5 de `f"{nombre_desarrollo.lower().strip()}{ciudad.lower().strip()}{fuente_nombre.lower()}"`.
- Antes de escribir en `lanzamientos.csv`, calcular el hash y verificar si ya existe.
- Si existe: no duplicar. Solo actualizar `fecha_deteccion` si el nuevo dato es más reciente.
- Si no existe: agregar con `status_verificacion = nuevo`.
- La deduplicación cross-fuente (mismo desarrollo detectado en múltiples portales) es válida: se mantienen todas las filas con diferente `fuente_nombre`.

## 7. Manejo de Errores por Fuente

- Cada fuente es independiente. Un error en una fuente no detiene las demás.
- Registrar siempre el mensaje de error completo en `fuentes_lanzamientos.csv`.
- Errores comunes a manejar:
  - `ConnectionTimeout`: registrar como `error`, continuar.
  - `HTTPError 403/404`: registrar como `error`, no reintentar.
  - `HTTPError 429/503`: registrar, esperar y reintentar (ver regla 1).
  - `ParsingError`: registrar como `warning` si al menos parte del contenido fue parseado; como `error` si nada fue extraído.
  - `SSLError`: registrar como `error`, continuar.

## 8. RSS — Filtros de Contenido

Para la Capa 2, solo procesar artículos que cumplan al menos uno de estos criterios en título o descripción:

**Keywords positivas (incluir):**
`lanzamiento, preventa, nuevo desarrollo, nuevo proyecto, inaugura, presenta, abre ventas, inicia ventas, estrena, primera etapa, fase 1, preventa exclusiva, nuevo complejo`

**Keywords negativas (excluir aunque aparezcan keywords positivas):**
`segunda mano, usado, remodelado, seminuevo, alquiler de temporada, se renta, arrendamiento`

Si un artículo tiene keywords positivas Y negativas, excluirlo.
