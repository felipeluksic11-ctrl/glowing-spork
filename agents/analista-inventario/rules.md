# Analista Inventario — Rules

## 1. Tamaño de Batch

- Procesar exactamente 20 proyectos por ejecución (o los que queden si son menos de 20).
- El batch se define por proyectos únicos, no por documentos. Un proyecto con 3 archivos en Drive cuenta como 1 proyecto del batch.
- Después de cada batch, hacer flush a Supabase y actualizar `outputs/analista_inventario_state.json`.
- No continuar al siguiente batch en la misma ejecución. Diseñado para ser llamado repetidamente (cron o manual).

## 2. Detección de Moneda

- **Siempre detectar moneda.** Nunca subir un precio sin moneda asignada.
- Si la detección es ambigua y no se puede inferir con razonable confianza, registrar `moneda: null` y `moneda_confianza: "no_detectada"`.
- En proyectos de Riviera Maya/Yucatán: la moneda default de fallback es USD si el precio está entre 100,000 y 2,000,000.
- En proyectos de Ciudad de México o interior del país: la moneda default de fallback es MXN.
- Nunca modificar el precio numérico detectado. Solo clasificar la moneda.

## 3. Fuente de Datos

- Leer siempre desde `outputs/redsearch_marketplace.csv`.
- Validar que el archivo existe antes de comenzar. Si no existe, abortar con error claro.
- Ignorar filas donde `url_drive` esté vacía, sea `null`, o no comience con `https://drive.google.com`.
- Registrar cuántas filas fueron omitidas por `url_drive` inválida en el log de ejecución.

## 4. Output a Supabase

- Usar upsert, nunca insert simple. La clave de conflicto es `(desarrollo, numero_unidad)`.
- Si `numero_unidad` es null (no detectado en el documento), usar como clave: `(desarrollo, url_documento_origen, precio)`.
- Nunca eliminar registros existentes. Solo actualizar precio y disponibilidad.
- Si Supabase no está disponible, guardar en `inventario.csv` y reintentar en la próxima ejecución.

## 5. Output CSV

- El archivo `inventario.csv` es acumulativo. Cada ejecución hace append de las nuevas filas, no sobreescribe.
- Excepción: si se pasa el flag `--reset-csv`, vaciar el CSV y empezar desde cero.
- Headers del CSV (en este orden):
  ```
  desarrollo,numero_unidad,tipo,metros_construccion,metros_terraza,nivel_piso,precio,moneda,moneda_confianza,disponibilidad,url_documento_origen,fecha_extraccion
  ```

## 6. Parseo de Documentos

- **PDFs:** Intentar siempre la extracción de tablas primero (pdfplumber o equivalente). Si falla, caer a extracción de texto plano y parsear con regex.
- **Excel:** Procesar todas las hojas. Si hay múltiples hojas con datos de precios, concatenar todas.
- **Timeout por documento:** 60 segundos. Si el parseo tarda más, marcar como `timeout` y continuar.
- **Tamaño máximo de archivo:** 50 MB. Archivos más grandes: registrar warning y saltar.

## 7. Normalización de Tipos de Unidad

Mapear variaciones de nomenclatura a los tipos estándar:

| Input detectado | Tipo normalizado |
|---|---|
| "Studio", "Estudio", "Loft" | `studio` |
| "1 recámara", "1BR", "1 Bed", "One Bedroom" | `1 rec` |
| "2 recámaras", "2BR", "2 Bed", "Two Bedroom" | `2 rec` |
| "3 recámaras", "3BR", "3 Bed" | `3 rec` |
| "4+ recámaras", "4BR+" | `4+ rec` |
| "Penthouse", "PH" | `penthouse` |
| "Local comercial", "Local", "Retail" | `local` |
| "Terreno", "Lote" | `terreno` |
| Cualquier otro | `otro` |

## 8. Manejo de Errores por Proyecto

- **Drive no accesible:** Registrar `[WARN]` y saltar al siguiente proyecto. No abortar la ejecución.
- **Ningún archivo de precios encontrado:** Registrar `[WARN]`. El proyecto se marca como `procesado_sin_datos` en el estado para no reintentar automáticamente.
- **Error de parseo:** Registrar `[ERROR]` con el mensaje. Reintentar 1 vez. Si falla de nuevo, marcar como `error` en el estado.
- **Error de Supabase en upsert:** Guardar las filas fallidas en `outputs/analista_inventario_failed.csv` para reproceso manual.
