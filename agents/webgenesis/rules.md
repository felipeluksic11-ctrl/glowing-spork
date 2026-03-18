# WebGenesis — Rules

## 1. Jerarquía de Modelos

- **Opus siempre supervisa.** Los agentes Supervisor de cada fase deben ser `claude-opus-4-6`. Nunca usar Sonnet para roles de supervisión.
- **Sonnet ejecuta.** Todos los Sub-Agentes operacionales deben usar `claude-sonnet-4-20250514`.
- **No mezclar roles.** Un Sub-Agente no puede tomar decisiones estratégicas que corresponden al Supervisor.

## 2. Concurrencia

- **Máximo 5 agentes concurrentes** en cualquier momento del proceso.
- Los Sub-Agentes dentro de una misma fase pueden correr en paralelo respetando este límite.
- Las fases son secuenciales: Fase N+1 no comienza hasta que Fase N esté en estado `completed`.
- Si hay 5 agentes activos, nuevas tareas entran a cola de espera (FIFO).

## 3. Crawling Responsable

- **Delay entre requests:** 2.5 segundos mínimo entre requests al mismo dominio.
- **Máximo 100 páginas por sitio.** Si el sitemap tiene más, priorizar: homepage, páginas de listings, páginas de categoría, páginas de contacto.
- **Respetar robots.txt.** Si un path está desallowed, no crawlear.
- **User-Agent declarado:** `WebGenesis-Bot/1.0 (competitive-analysis; contact: tech@propyte.mx)`
- **No crawlear en horarios pico** (9am-6pm hora local del servidor si es detectable).

## 4. Outputs

- Todo output se escribe en `./outputs/[nombre-proyecto]/`.
- Estructura de carpetas del proyecto generado:
  ```
  [nombre-proyecto]/
  ├── src/
  │   ├── app/
  │   ├── components/
  │   └── lib/
  ├── public/
  ├── package.json
  ├── next.config.js
  ├── tailwind.config.ts
  ├── tsconfig.json
  ├── .env.example
  └── README.md
  ```
- Los archivos de análisis intermedio se guardan en `./outputs/[nombre-proyecto]/intelligence/`.

## 5. Checkpoints en PostgreSQL

- Cada fase escribe su checkpoint al completarse, no durante la ejecución.
- Formato del campo `data`: JSON serializado con el output completo de la fase.
- Estados válidos: `pending`, `running`, `completed`, `failed`.
- El Meta-Orquestador debe verificar checkpoints al inicio de cada sesión antes de ejecutar.
- Nunca reejecutar una fase con estado `completed` a menos que se pase el flag `--force-phase=[N]`.

## 6. Manejo de Fallos

- Sub-Agente: máximo 3 reintentos con backoff exponencial (2s, 4s, 8s).
- Si falla después de 3 intentos: marcar tarea como `failed`, continuar con las demás tareas de la fase.
- Fase: si más del 40% de sub-tareas están en `failed`, detener y reportar al operador humano.
- Nunca ignorar silenciosamente un fallo. Siempre registrar en PostgreSQL con el error completo.

## 7. Calidad del Código Generado

- Todo código TypeScript debe ser tipado correctamente. No usar `any` excepto en casos justificados.
- Componentes React: functional components con hooks. No class components.
- Tailwind: no usar estilos inline. Todo via clases de Tailwind o variables CSS.
- El proyecto generado debe pasar `npm run build` sin errores antes de ser entregado.
- Incluir siempre: `.eslintrc.json`, `.prettierrc`, `tsconfig.json` con strict mode.

## 8. Competidores — Criterios de Inclusión/Exclusión

**Incluir:**
- Sitios con contenido de nicho relevante en posiciones 1-20 de SERP.
- Sitios con al menos 50 páginas indexadas.
- Dominios con DA (Domain Authority) > 10.

**Excluir:**
- Wikipedia, Wikimedia.
- YouTube, Vimeo y plataformas de video.
- Redes sociales (Instagram, Facebook, LinkedIn, TikTok).
- Directorios genéricos (Yelp, Yellow Pages, etc.).
- Sitios con Cloudflare anti-bot que bloqueen después de 3 intentos.
- Dominios con tiempo de respuesta > 10 segundos.
