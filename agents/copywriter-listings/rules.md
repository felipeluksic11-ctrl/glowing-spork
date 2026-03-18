# Copywriter Listings — Rules

## 1. Palabras y Frases Prohibidas

Las siguientes frases están absolutamente prohibidas en cualquier copy generado. El validador GPT-4o-mini debe detectarlas y devolver FAIL:

**Humo inmobiliario clásico:**
- "oportunidad única"
- "no te lo pierdas"
- "garantizado"
- "potencial ilimitado"
- "exclusivo" (sin dato concreto que lo respalde)
- "de lujo" (sin especificación de estándar)
- "plusvalía garantizada"
- "alta demanda"
- "el mejor precio del mercado"
- "inversión segura"
- "rentabilidad asegurada"
- "no pierdas esta oportunidad"
- "precio inmejorable"
- "oferta irrepetible"
- "diseño de vanguardia" (sin nombrar al arquitecto o firma)
- "amenidades de clase mundial"
- "concepto único en su tipo"
- "paraíso"
- "joya del Caribe"

**Superlativos vacíos:**
- "el más", "la más" (sin referencia comparativa verificable)
- "increíble", "espectacular", "impresionante" (cualquier adjetivo emocional sin dato)

**En inglés:**
- "one of a kind"
- "unique opportunity"
- "guaranteed returns"
- "world-class"
- "paradise"
- "gem of the Caribbean"
- "don't miss out"

## 2. Lead Protection — Regex de Validación Post-Generación

El validador debe escanear el copy generado con las siguientes reglas antes de aprobarlo:

**Patrones prohibidos (regex):**
```
# Teléfonos
(\+52|52)?[\s\-\.]?\(?\d{2,3}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{4}
\b\d{10}\b
WhatsApp|WA|Tel\.|Cel\.|Llama al

# Emails
[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}

# URLs y dominios
https?://[^\s]+
www\.[^\s]+
\.com|\.mx|\.io|\.co (en contexto de URL)

# Redes sociales
@[a-zA-Z0-9_]+
instagram\.com|facebook\.com|tiktok\.com|linkedin\.com
```

**Resultado:** Si cualquiera de los patrones tiene match, el validador devuelve:
```json
{
  "resultado": "FAIL",
  "razon": "Patrón detectado: [tipo de patrón] en posición [X]"
}
```

## 3. Brand Voice Anti-Humo

**Tono correcto:** Informativo, directo, confiable, levemente aspiracional.
**Tono incorrecto:** Exaltado, urgente, vago, lleno de adjetivos.

Reglas de estilo:
- Oraciones de máximo 20 palabras.
- Voz activa preferida sobre voz pasiva.
- Números siempre en cifras (72 m², no "setenta y dos metros cuadrados").
- Unidades de medida siempre: m², km, min, %, USD, MXN.
- Fechas de entrega: formato "Q1/Q2/Q3/Q4 + año" (ej. Q2 2027).

## 4. Redirección Obligatoria a Asesor Propyte

Todo CTA debe terminar en Propyte. Formatos aceptados:

- "Consulta disponibilidad y condiciones con un asesor Propyte."
- "Agenda una visita a través de tu asesor Propyte."
- "Solicita la lista de precios actualizada con un asesor Propyte."
- "Tu asesor Propyte puede confirmar disponibilidad y unidades vigentes."

Formatos NO aceptados:
- Cualquier mención a contactar directamente al desarrollador.
- Links o teléfonos directos.
- "Contáctanos" sin especificar que es Propyte.

## 5. Proceso de Validación

```
[Copy generado en ES] → [GPT-4o-mini validador]
  ├── Scan regex lead protection
  ├── Scan palabras prohibidas
  ├── Verificar estructura 5 bloques
  └── PASS → entregar output
      FAIL → devolver razón → re-generar (máx. 2 intentos)
```

Si después de 2 intentos el copy sigue fallando, el agente debe devolver el error con detalle para revisión humana.

## 6. Límites Operativos

- Máximo 2 regeneraciones por listing antes de escalar a revisión humana.
- El copy en español es siempre la fuente de verdad; el inglés es adaptación, no traducción literal.
- No generar copy sin al menos los campos: `tipo_propiedad`, `ubicacion_general`.
- Si faltan datos críticos (metraje, precio, fecha entrega), indicarlo como `null` en el output y no inventar valores.
