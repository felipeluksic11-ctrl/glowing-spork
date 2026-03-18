# Analista Rentas — Rules

## 1. Train/Test Split y Validación

- Train/test split siempre con `test_size=0.2` y `random_state=42` para reproducibilidad.
- El split se hace estratificado por `tipo_unidad` si hay suficientes datos por clase (mínimo 10 por clase).
- **Métricas obligatorias a calcular y registrar:**
  - MAE (Mean Absolute Error) en MXN
  - R² Score
  - MAPE (Mean Absolute Percentage Error)
- Registrar las métricas en el log y en la tabla `rental_model_runs` de Supabase si existe.
- **Umbrales de calidad:**
  - MAE < 15% del precio promedio → modelo aceptable
  - R² > 0.65 → modelo aceptable
  - Si ambos umbrales fallan: registrar warning y no hacer upsert de estimaciones (preservar estimaciones anteriores).
  - Si uno de los dos falla: registrar warning pero proceder con el upsert.

## 2. Métricas Financieras

Las siguientes métricas son obligatorias para cada combinación `(desarrollo, tipo_unidad)`:

| Métrica | Descripción | Unidad |
|---|---|---|
| `roi_5_anios` | ROI simple sin plusvalía a 5 años | % decimal (ej: 0.35 = 35%) |
| `irr_10_anios` | IRR con flujos de caja + venta al año 10 | % decimal anual |
| `cap_rate` | Renta neta anual / Precio de venta | % decimal |
| `gross_yield` | Renta bruta anual / Precio de venta | % decimal |
| `breakeven_meses` | Meses para recuperar inversión via rentas | Entero |

- Nunca dividir por cero. Si `precio_venta_promedio` es null o 0, omitir las métricas financieras para esa combinación y registrar warning.
- Si `n_comparables_usados` < `min_comparables` (default 5), no generar estimación. Registrar `[SKIP]` en log.
- Los valores de `irr_10_anios` que resulten negativos son válidos. No filtrar, registrar como están.

## 3. Upsert a Supabase

- Usar siempre upsert (INSERT ... ON CONFLICT DO UPDATE). Nunca DELETE + INSERT.
- Clave de conflicto para `rental_ml_estimates`: `(desarrollo, tipo_unidad)`.
- Clave de conflicto para `development_financials`: `(desarrollo, tipo_unidad)`.
- Incluir siempre `fecha_calculo` / `fecha_estimacion` con la fecha de ejecución actual.
- Si el upsert falla para una fila específica, continuar con las demás. No abortar la ejecución completa.
- Registrar el número total de filas upserted al finalizar.

## 4. Normalización de Moneda

- Todo el pipeline trabaja en MXN internamente.
- Si `rental_comparables` tiene precios en USD, convertir usando el tipo de cambio del día.
- El tipo de cambio se obtiene de una API pública (Banxico, ExchangeRate-API, o similar).
- Si no se puede obtener el tipo de cambio, usar el último registrado en caché o usar 17.5 MXN/USD como fallback de emergencia.
- Registrar el tipo de cambio usado en el log de ejecución.

## 5. Manejo de Outliers

- Antes de entrenar, eliminar outliers de `precio_renta_mensual` usando el método IQR por `tipo_unidad`.
- Registrar cuántos registros fueron eliminados como outliers en el log.
- No eliminar outliers del set de estimaciones (se estiman con el modelo, no con los datos raw).

## 6. Ejecución y Logging

- Al inicio de cada ejecución, registrar:
  ```
  [START] analista-rentas - 2026-03-18T05:00:00Z
  [DATA] N comparables cargados, M desarrollos en inventory
  [TRAIN] N_train registros, N_test registros
  [METRICS] MAE: X, R2: Y, MAPE: Z%
  [ESTIMATES] K estimaciones pre-computadas
  [FINANCIALS] K métricas financieras calculadas
  [UPSERT] rental_ml_estimates: N rows, development_financials: M rows
  [END] Duración: Xs
  ```
- Si cualquier paso falla con excepción, registrar el traceback completo y continuar con el siguiente paso cuando sea posible.

## 7. Supuestos Financieros por Defecto

Estos valores se pueden sobreescribir via argumentos de línea de comandos o variables de entorno:

| Parámetro | Default | Variable de entorno |
|---|---|---|
| Ocupación estimada | 75% | `OCUPACION_ESTIMADA` |
| Gastos operativos | 15% | `GASTOS_OPERATIVOS_PCT` |
| Plusvalía anual | 5% | `PLUSVALIA_ANUAL_PCT` |
| Horizonte IRR | 10 años | `HORIZONTE_IRR_ANOS` |
| Horizonte ROI | 5 años | `HORIZONTE_ROI_ANOS` |
| Tipo de cambio fallback | 17.5 MXN/USD | `USD_MXN_FALLBACK` |
