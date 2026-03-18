# Scraper Rentals — Rules

## 1. Deduplicación por Hash

- El `hash_id` es la clave de deduplicación primaria del dataset.
- Cálculo: `md5(f"{ciudad}{zona}{tipo_propiedad}{recamaras}{metros_construccion}{precio_renta_mensual}{moneda}".lower().replace(" ", ""))`.
- Antes de cada append al CSV, verificar que el `hash_id` no existe en el archivo.
- Si el hash ya existe y el precio cambió, actualizar el precio y `fecha_scraping` en el registro existente (no duplicar).
- Si el hash ya existe y el precio es igual, no modificar nada.

## 2. Output a CSV

- **Archivo destino:** `outputs/rental_comparables.csv`
- **Modo:** append con deduplicación por hash. Nunca truncar el histórico.
- **Crear directorio si no existe:** `os.makedirs("outputs", exist_ok=True)`
- **Headers del CSV** (en este orden exacto):
  ```
  hash_id,id_externo,titulo,tipo_propiedad,ciudad,zona,estado,
  recamaras,banos,metros_construccion,metros_terreno,amenidades,
  precio_renta_mensual,moneda,url_listing,fecha_publicacion,
  fecha_scraping,plataforma,is_active
  ```
- Si el archivo no existe en la primera ejecución, crearlo con los headers.
- Escribir en UTF-8 con BOM (`utf-8-sig`) para compatibilidad con Excel.

## 3. Gestión de is_active

Al final de cada ejecución completa:
1. Obtener la lista de `hash_id` extraídos en esta ejecución.
2. Para todos los registros en el CSV donde `is_active = True` y `plataforma = "lamudi"`:
   - Si su `hash_id` NO está en la lista de la ejecución actual: actualizar `is_active = False`.
   - Si su `hash_id` SÍ está: mantener `is_active = True`.
3. Este proceso detecta listings dados de baja en Lamudi sin eliminarlos del histórico.

## 4. GitHub Actions Cron

El workflow de GitHub Actions (`scrape-rentals.yml`) debe:

```yaml
schedule:
  - cron: "0 11 * * 1"  # Cada lunes 5AM CST (UTC-6 → 11:00 UTC)
```

**Variables de entorno requeridas en el repositorio (GitHub Secrets):**
- `SUPABASE_URL` (si se hace upload a Supabase en el futuro)
- `SUPABASE_KEY` (si aplica)

**Pasos del workflow:**
1. Checkout del repositorio.
2. Setup Python 3.11.
3. Install requirements (`pip install -r requirements.txt`).
4. Ejecutar `python scraper_rentals.py`.
5. Commit del CSV actualizado si hay cambios (`git diff --quiet || git commit`).
6. Push al branch.

## 5. Rate Limits de Lamudi

- **Delay entre requests:** 2-5 segundos aleatorios entre páginas de resultados.
- **Delay entre listings individuales:** 1-3 segundos.
- Si Lamudi devuelve HTTP 429: esperar 120 segundos y reintentar. Máximo 2 reintentos.
- Si Lamudi devuelve HTTP 403 o bloquea con CAPTCHA: registrar error y detener el scraping de esa URL. No reintentar en la misma ejecución.
- Máximo 500 listings por ciudad por ejecución para no saturar.

## 6. Rotación de User-Agent

Usar el mismo pool de User-Agents que scraper-lanzamientos:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]
```

## 7. Ciudades y Geografía Objetivo

**Quintana Roo — búsquedas por URL slug:**
- `cancun` → Ciudad: `Cancún`
- `playa-del-carmen` → Ciudad: `Playa del Carmen`
- `tulum` → Ciudad: `Tulum`
- `puerto-morelos` → Ciudad: `Puerto Morelos`
- `bacalar` → Ciudad: `Bacalar`
- `cozumel` → Ciudad: `Cozumel`

**Yucatán — búsquedas por URL slug:**
- `merida` → Ciudad: `Mérida`
- `progreso` → Ciudad: `Progreso`
- `valladolid` → Ciudad: `Valladolid`

La cobertura se limita a estas ciudades. No expandir a otros estados sin actualizar config.json.

## 8. Manejo de Errores

- Cada ciudad es independiente. Un error en una ciudad no detiene las demás.
- Registrar en el log al final de cada ciudad:
  ```
  [OK] Cancún - 87 nuevos registros, 12 actualizados, 5 desactivados
  [WARN] Holbox - 0 resultados encontrados (puede ser normal)
  [ERROR] Bacalar - HTTP 403 después de 2 reintentos
  ```
- Si el error es en la escritura del CSV (disco lleno, permisos), abortar inmediatamente con error claro.
- Logging de resumen al final de la ejecución completa:
  ```
  [SUMMARY] Total nuevos: N | Actualizados: M | Desactivados: K | Errores: J ciudades
  [OUTPUT] outputs/rental_comparables.csv - X filas totales (Y activos)
  ```

## 9. Normalización de Campos

- `recamaras` y `banos`: enteros. Si Lamudi muestra "Studio" o "0", registrar `0`.
- `metros_construccion`: float con 1 decimal. Si no disponible: `""`.
- `amenidades`: lista de amenidades separadas por `|`. Normalizar a minúsculas. Ej: `"alberca|gym|estacionamiento"`.
- `moneda`: detectar automáticamente desde el símbolo en el listing (`$` → MXN en contexto México; `USD` o `US$` → USD). Default: `MXN`.
- `precio_renta_mensual`: float, sin comas, sin símbolo de moneda. Solo el número.
