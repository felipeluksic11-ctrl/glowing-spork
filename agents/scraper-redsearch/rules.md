# Scraper RedSearch — Rules

## 1. Variables de Entorno Requeridas

El agente no puede ejecutarse sin las siguientes variables de entorno:

```bash
REDSEARCH_EMAIL=tu_email@ejemplo.com
REDSEARCH_PASS=tu_contraseña
```

Al iniciar, verificar que ambas variables existen y no están vacías:

```python
import os
email = os.environ.get("REDSEARCH_EMAIL")
password = os.environ.get("REDSEARCH_PASS")

if not email or not password:
    raise EnvironmentError(
        "REDSEARCH_EMAIL y REDSEARCH_PASS son requeridas. "
        "Configúralas como variables de entorno antes de ejecutar."
    )
```

Si alguna falta, abortar la ejecución con mensaje de error claro. No continuar.

## 2. Output al CSV

- **Archivo destino:** `outputs/redsearch_marketplace.csv`
- **Modo:** overwrite completo en cada ejecución. El CSV representa siempre el estado actual del marketplace.
- **Crear directorio si no existe:** `os.makedirs("outputs", exist_ok=True)`
- **Headers del CSV** (en este orden exacto):
  ```
  desarrollo,barrio_colonia,ciudad,desarrollador,numero_contacto,
  unidades_disponibles,unidades_totales,contacto_nombre,contacto_email,
  url_drive,inicio_ventas,fecha_entrega,comision,url_listing,fecha_scraping
  ```
- Nunca escribir el CSV hasta que todos los listings hayan sido procesados (o la ejecución se interrumpa). Escribir en memoria primero, luego volcar al archivo.
- Excepción: si hay más de 500 listings, hacer flush parcial cada 100 listings para no perder progreso.

## 3. Autenticación por Sesión

- Usar sesión HTTP con cookies (requests.Session o Playwright con context persistente).
- La sesión debe mantenerse activa durante toda la ejecución.
- Si se detecta redirección al login durante el scraping (la sesión expiró): re-autenticar y reintentar el request actual.
- Máximo 1 re-autenticación por ejecución. Si la segunda autenticación también falla, abortar.
- Nunca guardar las credenciales en el código, en logs, o en el CSV de output.

## 4. Delays Aleatorios

- **Entre requests al mismo dominio:** espera aleatoria entre 1.5 y 4 segundos.
- Implementar con `time.sleep(random.uniform(1.5, 4.0))`.
- No hacer requests concurrentes al mismo dominio.
- Si se procesan más de 100 listings, hacer una pausa de 10-15 segundos cada 50 listings para simular comportamiento humano.

## 5. Manejo de Campos Faltantes

- Si un campo no se encuentra en el HTML del listing, registrar como cadena vacía `""` en el CSV (no `null`, no `None`, no `NaN`).
- Excepción: `unidades_disponibles` y `unidades_totales` deben ser enteros o cadena vacía. No valores como "consultar" o "N/A" — normalizar a `""`.
- Si `url_drive` no se encuentra, registrar `""`. El analista-inventario filtra por este campo.
- Si `desarrollo` no se puede extraer (campo crítico), omitir el listing y registrar un warning en el log.

## 6. Logging de Ejecución

```
[START] scraper-redsearch - 2026-03-18T10:00:00Z
[AUTH] Login exitoso para usuario: ***@ejemplo.com
[DISCOVERY] 127 listings encontrados en el marketplace
[PROGRESS] 10/127 procesados...
[PROGRESS] 50/127 procesados...
[PROGRESS] 100/127 procesados...
[COMPLETE] 127/127 procesados - 3 con errores
[OUTPUT] outputs/redsearch_marketplace.csv - 124 filas escritas
[END] Duración: 342s
```

- Nunca mostrar el email o password completos en los logs. Usar `***@dominio.com` para el email.
- Registrar cada listing con error como `[WARN] listing_url - campo_faltante: desarrollo`.

## 7. Validación Post-Scraping

Después de escribir el CSV, ejecutar validaciones:

1. Verificar que el número de filas en el CSV coincide con el número de listings procesados exitosamente.
2. Verificar que `desarrollo` no está vacío en ninguna fila.
3. Verificar que `ciudad` está dentro del set de ciudades conocidas de la Península de Yucatán.
4. Reportar en el log: total de filas, % con `url_drive` válida, % con `fecha_entrega` detectada.

Ejemplo de reporte final:
```
[VALIDATION] 124 filas totales
[VALIDATION] url_drive válida: 89/124 (71.8%)
[VALIDATION] fecha_entrega detectada: 102/124 (82.3%)
[VALIDATION] comision detectada: 118/124 (95.2%)
```

## 8. Limitaciones de Uso

- No usar este scraper para fines distintos a la actualización del inventario de Propyte.
- No compartir el CSV resultante con terceros sin autorización.
- Las credenciales de TheRedSearch son propiedad del usuario; no almacenarlas ni transmitirlas a servicios externos.
- Respetar los Términos de Servicio de TheRedSearch en cuanto a frecuencia y volumen de acceso.
