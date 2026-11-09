# MaesTrials — Plan de trabajo

> App propia (no comercial) que detecta los reels ganadores de la cuenta de Jose,
> crea versiones distintas de verdad y las publica solas como Trial Reels cada día.
> Cuentas: la de Jose (~10.000 seguidores, ~40 reels, ya tiene la opción Trial Reel) y, más adelante, la del socio.

Última actualización: 2026-11-09

---

## 1. Lo que sabemos (research, con fuente)

### Cómo funciona TrialPilot (la referencia)
| Pieza | Qué hacen | Fuente |
|---|---|---|
| Conexión | API oficial de Instagram, sin contraseña | Panel de trialpilot.io |
| Ganadores | Reel que supera al 80 % de tus últimos 60 reels (90 días). Mín. 5 reels medidos. Un ganador vale 180 días | `GET /api/mi/cuentas` (campo `reglas`) |
| Publicar | Máx. 10/día, mín. 30 min entre subidas (avisan < 45 min) | Su API y `tp-app.js` |
| Regla del feed | Máx. 6 Trial Reels por cada reel del feed (últimos 7 días) | `POR_CADA_REEL = 6` en su código |
| Texto | Caption original reescrito con IA en cada subida, o frases CTA. 1 de cada 5 sin texto | Código + /condiciones |
| Proveedores | Railway, RunPod (vídeo), OpenRouter (IA), HikerAPI, Whop, Twilio | trialpilot.io/privacidad |
| Precio | 100 €/mes por cuenta | trialpilot.io |

Copia de su código del panel: `.playwright-mcp/tp-app.js`.

### Lo que dicen sus datos (su blog, 1.810 trial reels)
- Hasta 11/día: ~4 % se quedan en 0. **12 o más al día: 31 % en 0.**
- Cada vídeo, **máx. 3 veces por semana**. Se "quema" tras 7-9 subidas en ~4 días.
- Si una versión se queda en 0, la siguiente del mismo vídeo se queda en 0 el 80 % de las veces.
- Instagram saca huella de imagen y de sonido: **recortar 1 s, un filtro, otro texto o cambiar metadatos NO basta**. Hay que cambiar encuadre, composición, ritmo y audio.

### API oficial de Meta (documentación oficial)
- Trial Reels por API: `POST /<IG_ID>/media` con `media_type=REELS` + `trial_params.graduation_strategy` = `MANUAL` o `SS_PERFORMANCE` (changelog 3-dic-2025).
- Límite: 100 publicaciones por API cada 24 h.
- Métricas por reel: `views`, `comments`, `likes`, `shares`, `saved`, `reach`… (hasta 48 h de retraso).
- Con "Instagram Login" el vídeo tiene que estar en una **URL pública** al publicar.
- Vídeo: MP4/MOV, H264/HEVC + AAC, 3 s a 15 min, máx. 300 MB, 23-60 fps, 9:16.
- App en **modo desarrollo** con acceso estándar: sirve para cuentas con rol en la app. **No hace falta publicarla ni pasar revisión.**

### Vercel (documentación oficial)
- Hobby (gratis): funciones de máx. 300 s, 2 GB / 1 vCPU, **4 h de CPU al mes**. Solo uso personal no comercial.
- Cron clásico en Hobby: 1 vez al día. **Schedules (beta) en Hobby: cada 15 min**, 5.000 ejecuciones al mes.
- Blob en Hobby: 1 GB guardado, 10 GB de descarga al mes, URLs públicas. Si te pasas, se bloquea 30 días.
- Pro: 20 $/mes (incluye 20 $ de consumo), funciones de hasta 800 s y 4 GB / 2 vCPU.

---

## 2. Decisiones tomadas
- [x] Usar la API oficial de Instagram (app de Meta en modo desarrollo, sin publicarla).
- [x] Alojar en Vercel.
- [x] Criterio de ganador (lo eligió Claude): un reel del feed de los últimos 180 días, con al menos 48 h de vida, gana si está en el **top 20 % por visitas** (percentil 80) **O** supera un **umbral fijo de visitas**. Como los vídeos de IA de Jose funcionan muy bien, el umbral fijo recoge más ganadores. La cifra del umbral se fija con los datos reales de la Fase 1 (no se inventa).
- [x] Volumen inicial: **3 trial reels al día**, separados 45 min o más. Se sube hasta 10 cuando haya ganadores de sobra.
- [x] D1. Montaje de vídeos con ffmpeg en **GitHub Actions** (2026-11-09).
- [x] D2. **Vercel Pro** (20 $/mes) (2026-11-09).
- [x] D3. IA del caption: **API de Claude**. Jose tiene clave; se guarda como variable de entorno, nunca en el chat ni en el código (2026-11-09).
- [x] D4. Feed: ahora 1 reel al día o cada 2 días; Jose quiere pasar a **2-3 al día**. Con la regla 1 feed por cada 6 trials, así caben hasta 12-18 trials al día; el tope sigue en 10 (2026-11-09).

## 3. Pendiente de decidir (Jose)
- [x] Clave de la API de Claude en `.env` (`ANTHROPIC_API_KEY`). La metió Jose (9-nov). Se prueba en la Fase 3.

## 3b. Conexión con Meta (hecha el 2026-11-09)
- App **MaesTrials**, ID `1198791455807715`, en modo desarrollo y sin publicar. Porfolio: José María Garcia Gómez.
- Las apps nuevas ya **no** usan "Instagram Login": usan **Inicio de sesión unificado**. La base es `graph.facebook.com/v27.0` (no `graph.instagram.com`).
- Configuración `1157464596663579` con 7 permisos: instagram_basic, instagram_content_publish, instagram_manage_insights, instagram_manage_comments, instagram_manage_messages, ads_management y ads_read.
- @josenews.ai es "Evaluador de Instagram" (ID IG `17841438323050307`). Negocio compartido: "Jose | News AI".
- Token de usuario del sistema: **no caduca nunca**. Está guardado en `.env`, que no se sube a ningún sitio (`.gitignore`).
- Fase 0 comprobada: la API devuelve 102 publicaciones (83 reels) con visitas, alcance, compartidos y guardados.

## 3c. Datos reales de @josenews.ai (2026-11-09)
- 10.062 seguidores. 83 reels entre el 29-jul y el 28-oct-2026. `media_count` dice 37; **sin verificar** por qué no coincide (puede que la lista incluya trial reels).
- Visitas por reel: mediana 1.310, media 5.358, máximo 119.114, mínimo 0.
- Por publicación (sin agrupar): percentil 80 = 3.507 visitas → 17. Con 10.000 o más visitas: 10 reels; con 20.000 o más: 6.
- **Superado por la Fase 2:** lo que cuenta es el vídeo, no la publicación → 63 vídeos, P80 = 3.120, **12 ganadores**. Con la regla de 4 días: 12 ÷ 4 ≈ **3 trials al día**.

---

## 4. Arquitectura (simple)

```
[Vercel Schedules cada 15 min] → función "¿toca publicar?"
        │
        ├─ lee métricas por la API de Instagram → elige ganadores → guarda en la base de datos
        ├─ coge la siguiente versión ya montada (Vercel Blob, URL pública)
        └─ crea el contenedor con trial_params → espera FINISHED → publica → borra el vídeo del Blob

[Montaje de vídeo con ffmpeg]  ← D1 decidido: GitHub Actions
   GitHub Actions (gratis, ~2.000 min/mes en repo privado): 1 vez al día monta las versiones del día y las deja en una URL pública. Automático.
   (Descartadas: dentro de Vercel y en el PC de Jose.)
   Hoy (Fase 1) los vídeos se sirven desde public/v/ con commit + push, no desde Blob.

[Panel web en Vercel]: ganadores, calendario, resultados a 24 h y botón de pausa.
```

Base de datos: una Postgres gratis del Marketplace de Vercel (Neon). Los límites de su plan gratis están **sin verificar**.

---

## 5. Fases (una cada vez y con comprobación)

### Fase 0 — Preparación (con Jose) ✅ HECHA 2026-11-09
- Crear la cuenta de desarrollador de Meta y la app en modo desarrollo, con **inicio de sesión unificado** (ver 3b).
- Dar rol a la cuenta de Instagram de Jose y sacar el token (de usuario del sistema: **no caduca**).
- **Comprobación:** la API devuelve 102 publicaciones (83 reels) con sus métricas.

### Fase 1 — Pasada de punta a punta con datos reales (desde el PC) ⏳ PUBLICADO, MIDIENDO
**Resultado (2026-11-09):**
- Ganador: reel `18129515419637342` ("La IA que está cambiando la forma de analizar la bolsa", 119.120 visitas).
- Versión 1 con ffmpeg (`fase1/pasada.py`): zoom 1,10, velocidad 1,05, saturación 1,08 y contraste 1,04. **ffmpeg tardó 4 s** para 56 s de vídeo.
- La API da el vídeo a **720x1280** (ya comprimido por Instagram). Para mejorar la calidad, mejor partir de los archivos originales de Jose.
- URL pública: `https://maestrials.vercel.app/v/<archivo>.mp4` (carpeta `public/v/` del repo).
- **Trial reel publicado:** `18416510161083451` → https://www.instagram.com/reel/DfhVYMrFWa_/ (12:30 UTC). La API aceptó `trial_params` MANUAL y `is_shared_to_feed: false`.
- ✅ Jose confirma en la app que sale como **Trial reel**. ✅ Su automatización de "comenta PALABRA" funciona también en los trials.
- Calidad: Jose da por buena la de la API (720p). No hace falta buscar los originales.
- Visitas a los 5 min: 0 (normal: Meta avisa de que las métricas pueden tardar hasta 48 h). Se mide a las 24 h (10-nov, 12:30 UTC).
- **Lectura provisional a las 2,4 h (9-nov, 14:53 UTC):** 361 visitas, 262 de alcance, 3 me gusta, 2 comentarios, 1 compartido, 7 guardados, 10,8 s de tiempo medio visto. Ya supera el techo de los trials muertos (≤ 300 visitas).
- Jose decide (9-nov) **no esperar a las 24 h para arrancar la Fase 3**. La medida de 24 h se toma igual y sirve de control.

**Cómo se despliega en Vercel (importante):**
- Solo con commit + push al repo privado `eternitydevzz/maestrials`. Hacerlo desde el panel de Vercel pide un código por email que no llega.
- El autor del commit tiene que ser `eternitydevzz <336098555+eternitydevzz@users.noreply.github.com>` (configurado en este repo). Si no, Vercel marca el despliegue como "Blocked".
- Push con la credencial de gh: `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push`.
- Proyecto Vercel: `info-79696548s-projects/maestrials` (equipo Eternity Group, plan Pro).
- Leer los reels y sus `views` y `comments`, elegir 1 ganador, descargarlo, montar 1 versión con ffmpeg, subirla a una URL pública y publicarla como trial reel `MANUAL`.
- Medir cuánto tarda ffmpeg por versión (sirve para decidir D1).
- **Comprobación:** Jose ve el trial reel en su Instagram y sus visitas a las 24 h.
- **Hasta que Jose no lo vea funcionar, no se construye lo siguiente.**

### Fase 2 — Detector de ganadores ✅ HECHA 2026-11-09 (`fase2/ganadores.py`)
**Resultado:**
- `is_shared_to_feed=false` = trial reel (cuadra: 16 reels de feed + 19 fotos/carruseles ≈ las 37 que dice la cuenta). Jose ya había subido unos 65 trials a mano.
- Lo que gana es el **vídeo**, no la publicación. Las publicaciones del mismo vídeo se agrupan **solo con una huella de fotogramas** (dHash de los segundos 3 y 8, distancia ≤ 8). La **portada no sirve**, porque Jose pone portadas distintas al mismo vídeo, y el pie tampoco (ver los fallos arreglados más abajo). Se comprobó a ojo con 2 grupos.
- 83 publicaciones → **63 vídeos distintos**. Corte P80 = 3.120 visitas → **12 ganadores**. (La primera versión daba 52 vídeos y 10 ganadores, que Jose dio por buenos; tras el arreglo salen 2 más.) Con la regla de 4 días salen unos 3 trials al día.
- Datos de Jose: las repeticiones con **otro texto de gancho** a veces funcionan (un trial repetido hizo 14.446 visitas) y otras se quedan en 0 (repeticiones con 0-8 visitas). Instagram sí detecta los repetidos.
- Pendiente para la Fase 5: Jose quiere poder **añadir ganadores a mano**.

#### Plan original de la Fase 2
- Percentil 80 + umbral opcional. Lista de ganadores con sus números.
- **Comprobación:** Jose revisa la lista y confirma que son sus mejores reels.

### Análisis de los trials que ya subió Jose (2026-11-09, 84 publicaciones, datos en `trabajo/analisis_trials.json`)
- **El espacio entre repeticiones es lo que más pesa.** Repeticiones del mismo vídeo (cuerpo igual, distancia ≤ 8):
  - **≥ 9,5 días** desde la publicación anterior de ese vídeo: **10 de 10 funcionaron** (más de 1.000 visitas; mediana 4.968; hasta 42.610).
  - **≤ 2,1 días**: **7 de 10 murieron** (300 visitas o menos; mediana 6). Sin datos entre 3 y 9 días.
  - (Recalculado el 9-nov con el agrupado corregido; antes salían 9/9 y 6/10.)
- **Cambiar el gancho no explica el éxito.** Repeticiones idénticas (mismo gancho y mismo pie) con espacio largo hicieron 42.610, 7.186 y 2.675. Con espacio corto murieron incluso con el gancho muy cambiado.
- **Último reel de feed: 2-sep-2026.** Desde entonces solo trials (y carruseles hasta el 19-oct). Los vídeos nuevos que solo salieron como trial tienen una mediana de 78 a 830 visitas por semana; los de feed de agosto, de 2.848 a 24.720. **Los 10 ganadores tienen todos versión de feed.** Es correlación, no causa demostrada.
- **Lo que separa a un ganador de un vídeo flojo es la retención**: los ganadores se ven un 38 % (14,8 s de 44 s) y los flojos un 16 % (6,3 s); los ganadores tienen 12,5 compartidos por cada 1.000 visitas y los flojos 5,2.
- **Fallos de la Fase 2, ARREGLADOS el 9-nov:** (a) "mismo pie = mismo vídeo" juntaba vídeos distintos con pies genéricos → ahora se agrupa **solo por fotogramas**; (b) los grupos se nombraban por el pie y uno pisaba a otro (se perdía "Comenta N8N", 5.794 visitas) → ahora se nombran por id. Comprobado: 83 publicaciones = **63 vídeos**, sin perder ninguna. Corte P80 = 3.120 → **12 ganadores**.

**Decisiones de Jose (9-nov):**
- **Espacio mínimo entre publicaciones del mismo vídeo: 4 días** (zona sin datos: es un experimento que se mide). Con 12 ganadores salen unos 3 trials al día.
- Jose tiene **bloqueado el envío de DM en Instagram hasta el 17-nov-2026**. Por eso dejó de subir contenido. Riesgo (hipótesis): los pies con "Comenta PALABRA" generan DM automáticos. **Decisión (9-nov): se mantiene "Comenta PALABRA" en los pies de los trials** (opción B). El trial de hoy no se toca.
- **Predicción comprobable:** el trial de hoy (bolsa) sale unos 34 días después de la última publicación de ese vídeo (6-oct). Si el patrón se cumple, debería pasar de 2.000 visitas.

### Fase 3 — Variaciones "de verdad"
- Cada versión cambia varias cosas a la vez: encuadre (zoom/reencuadre distinto), composición (p. ej. vídeo sobre fondo desenfocado), ritmo (empieza en otro momento o lleva otra velocidad), audio (música de fondo o tono), gancho de texto en pantalla y caption reescrito con IA.
- **Hipótesis sin probar:** que esto evite la huella de Instagram. Se mide con el % de versiones en 0 visitas (objetivo < 10 %).
- **Comprobación:** Jose ve 3 versiones y las aprueba a ojo.

**Decisiones de Jose (9-nov):** arrancar sin esperar a las 24 h del trial de la bolsa; cambios **suaves**; el "gancho" es el **texto en pantalla**; hoy se suben **2 más** (3 en el día); los candidatos son los 3 de más retención que ya cumplen los 4 días; la regla "1 feed por cada 6 trials" queda **solo como aviso** (bloquearía todo: el último feed es del 2-sep).

**Hecho (9-nov, `fase3/variar.py`):**
- `preparar`: transcribe el vídeo con Whisper `small` (el audio lo saca ffmpeg), pide a Claude (`claude-opus-5-5`, salida JSON, `fallbacks: "default"`) un gancho de 2 líneas y el pie reescrito, y comprueba que el pie lleva la palabra clave exacta (si no, repite hasta 3 veces). Sortea cambios suaves (zoom 1,04-1,10, velocidad 1,00-1,05, color y empezar de 0 a 0,5 s más tarde) y los guarda en la ficha `trabajo/<id>/version_<clave>.json`.
- El gancho va en una caja **negra con letra blanca, arriba, solo los 3 primeros segundos** (la caja blanca no se veía sobre fondos blancos).
- `remontar` vuelve a montar una versión sin llamar a Claude. `publicar` exige la regla de 4 días y los 45 min entre subidas, y que el vídeo ya esté en la URL pública.
- Versiones listas: YO (`18007610888765552-f3-24bce52f`), API (`17901761979341450-f3-44adcba7`) y SKILL (`18024659621894106-f3-5e45f764`). ffmpeg tarda de 3 a 14 s por vídeo.
- Hallazgo: la huella de la Fase 2 no reconoce como "el mismo vídeo" la versión zoom 1,10 de la bolsa. La regla de 4 días se cuenta con el registro propio (`trabajo/publicaciones.json` + `publicado.json` de la Fase 1), no con la huella.
- Para la Fase 4: la regla de 4 días no ve las publicaciones que Jose suba a mano; habrá que cruzarla también con la huella.

### Panel web + autopilot (Fases 4 y 5 juntas) — decisiones de Jose (9-nov)
- **Cambio de orden pedido por Jose:** el panel (Fase 5) se hace junto con la publicación automática (Fase 4).
- Panel **web en Vercel** (`maestrials.vercel.app`), con contraseña (`PANEL_PASSWORD` en `.env` y en Vercel), estilo **claro y limpio**.
- Pantallas: **Ganadores**, **Versiones** (ver, editar gancho y pie, rehacer, aprobar y publicar), **Resultados** y **Añadir ganador a mano**.
- Botón **Publicar** con confirmación + interruptor de **autopilot**: con él encendido **publica sin pedir aprobación**, solo de **9:00 a 22:00 hora de Nueva York** (America/New_York, con cambio de hora), 3 al día, ≥ 45 min entre subidas, 4 días entre publicaciones del mismo vídeo y aviso del feed 6:1.
- Técnica: páginas HTML ligeras + funciones Python en Vercel que reutilizan el código de las fases 1-3; base de datos Neon Postgres; vídeos en Vercel Blob; montaje (ffmpeg + Whisper + Claude) en GitHub Actions (D1).
- **Paso 0 (Jose):** `VERCEL_TOKEN` en `.env` (equipo Eternity Group) y permiso `workflow` en `gh` (`gh auth refresh -h github.com -s workflow`).
- Pasos: 1) Ganadores + Resultados con datos reales y contraseña (primer entregable, se comprueba desde el móvil) → 2) Versiones con GitHub Actions + Blob + publicar → 3) Añadir ganador a mano → 4) Autopilot (comprobación: 3 días seguidos sin tocar nada).

**Paso 1, estado (9-nov, 17:45 h de España):** hecho y probado **en local** (`python -I -X utf8 herramientas/servidor_local.py` → http://localhost:8787), sin subir.
- Archivos: `api/panel.py` (función de Vercel), `api/_panel/` (config, auth, instagram, datos, rutas), `public/index.html`, `entrar.html`, `panel.css`, `panel.js`.
- Probado: contraseña mala → "Contraseña incorrecta"; sin sesión → te manda a Entrar; Ganadores (12, 9 disponibles, con miniaturas) y Resultados (3 trials) con datos reales, en 1,8-1,9 s.
- `fase2/ganadores.py` ahora guarda también retención, duración, fecha de la última publicación e ids de cada vídeo (mismas cifras: 63 vídeos, P80 = 3.120, 12 ganadores).
- La API de Instagram ya no admite `?ids=` (retirado en la v26): se pide un reel por llamada, en paralelo.
- Falta para tenerlo en Vercel: el Paso 0 de Jose (token de Vercel y permiso `workflow`), la base de datos y subir los datos de `trabajo/` a ella.
- **Fallo encontrado (sin arreglar, pendiente de Jose):** `ganadores.py` solo excluye como "de MaesTrials" la publicación de la Fase 1; las de la Fase 3 (`trabajo/publicaciones.json`) las contaría como reels de Jose pasadas 48 h.

### PLAN B (decisión de Jose, 9-nov): sin panel de Vercel
- **Por qué:** a Jose no le llega el email de verificación de Vercel (lleva 2 días). Sin eso no hay token, ni `vercel login`, ni variables, ni base de datos, ni logs. La función `api/panel.py` sale con 404 en Vercel y no se puede ver por qué.
- **Cómo:** el trabajo lo hace **GitHub Actions** (las claves van como secretos de GitHub; los sube Jose con un comando de PowerShell, porque el sistema de permisos no me deja hacerlo a mí). Los datos viven en el repo, en `datos/`. **Vercel solo sirve los vídeos** de `public/v/` (eso funciona con push). El **panel se usa en el PC** (`herramientas/servidor_local.py`).
- Registro único de trials: `datos/publicaciones.json` (incluye el de la Fase 1). Lo leen `fase3/variar.py`, `fase2/ganadores.py` y el panel.
- `vercel.json` → `ignoreCommand`: Vercel solo despliega si cambian `public/`, `api/` o `vercel.json` (los commits de datos no gastan despliegues).
- Pasos: **B1** medir solo (`automatico/medir.py` + `.github/workflows/medir.yml`, cada 2 h; foto de 24 h entre las 24 y las 26 h, con la hora exacta) → **B2** montar solo en Actions → **B3** autopilot en horas fijas (propuesta: 10:00, 14:00 y 19:00 NY; sin confirmar) → **B4** panel en el PC (Versiones, interruptor, Publicar ahora, Añadir ganador, Resultados a 24 h) y sacar el panel de `public/` → **B5** 3 días sin tocar nada.
- **B1 hecho (9-nov):** secretos en GitHub (los subió Jose); run 42666742058 midió los 3 trials y guardó `datos/` (commit 0b13435); Vercel se saltó ese commit ("Canceled by Ignored Build Step"). **Falta la prueba de verdad:** la foto de 24 h de la bolsa, sola, el 10-nov entre las 12:30 y las ~14:30 UTC.
- **B2 hecho (9-nov):** run 42668922622 (2 min y medio) preparó 2 versiones: 18107396678277689 "Si Claude Code / llega al límite..." (CÓDIGO) y 17942022420269999 "80 modelos de IA / gratis en un sitio" (API). Textos revisados contra la transcripción; Vercel las sirve (tamaños iguales). Fuente del gancho: **Archivo Black** (OFL, en `recursos/fuentes/`), porque Arial Black no existe en Linux ni se puede subir. Cola: SKILL + estas 2 = 3. **Falta:** que Jose las apruebe a ojo.
- Decisiones de Jose (9-nov): horas de publicación **10:00, 14:00 y 19:00 NY**; SKILL lo publicará el autopilot. Jose aprobó a ojo las 2 versiones del B2.
- **B3 hecho (9-nov):** `automatico/publicar.py` + `.github/workflows/autopilot.yml` (cada hora, minuto 7 UTC: mide y publica si toca). Interruptor y horarios en `datos/ajustes.json`. Si GitHub se salta un hueco, lo recupera en la hora siguiente (con 45 min de separación y sin pasar de 3). La publicación se apunta nada más hacerse (para no repetirla si algo falla después). Probado: 7 casos de horario en el PC y run 42672519285 en GitHub ("hueco ya cubierto", midió y guardó). `medir.yml` queda solo manual. **Falta la prueba de verdad:** el 10-nov hacia las 15:07 UTC (10:07 NY) tiene que publicar SKILL solo; después, las 2 del B2 a las 14:00 y 19:00 NY.
- Gasto estimado de Actions: autopilot ≈ 720 min/mes + preparar ≈ 90 min/mes ≈ 810 min/mes (sin verificar el cupo del plan de Jose).
- `tzdata` instalado en el Python del PC (Windows no trae zonas horarias).
- Riesgos: minutos de Actions (2.000/mes en repo privado gratis, **plan de Jose sin verificar**; cálculo ≈ 1.000-1.200/mes); el repo crece con los vídeos (≈ 0,8 GB/mes con 3 al día); hay **dos proyectos de Vercel** (`maestrials` y `maestrials-4odv`) desplegando el mismo repo.

### Fase 4 — Publicación automática en Vercel
- Schedules cada 15 min, N al día, separación de 45 min o más, **mínimo 4 días entre publicaciones del mismo vídeo** (decisión de Jose, sustituye a "máx. 3 veces por semana").
- Si una versión se queda en 0, ese vídeo se descansa. Regla 1 feed por cada 6 trials.
- **Comprobación:** 3 días seguidos publicando solo, sin que Jose toque nada.

### Fase 5 — Medición y panel
- Visitas a las 24 h de cada versión, qué variación funciona mejor y vídeos quemados.
- **Comprobación:** Jose entiende el panel sin explicación.

### Fase 6 — Cuenta del socio
- Darle rol en la app de Meta, conectar su cuenta y separar los datos por cuenta.

---

## 6. Riesgos
- **R1.** Instagram puede bajar el alcance o desactivar los Trial Reels si se abusa (lo avisan las condiciones de TrialPilot). Por eso se empieza con 3 al día.
- **R2.** Que las variaciones no superen la huella de Instagram → versiones en 0. Se mide en la Fase 3.
- **R3.** Con la regla de 4 días, para 10 trials al día hacen falta unos 40 ganadores. Hoy hay 12 (≈ 3 al día). Solo crece con vídeos nuevos que ganen (o añadiendo ganadores a mano).
- ~~**R4.** El token caduca a los 60 días.~~ Resuelto: el token de usuario del sistema no caduca nunca.
- **R5.** Pasar un trial reel al feed no se elige por API: `MANUAL` (lo pasa Jose) o `SS_PERFORMANCE` (lo pasa Instagram).

## 7. Apuntado para más adelante
- Contenido de IA: comprobar si la API permite marcar la etiqueta "Información de IA" de Meta y si hace falta en estos vídeos. **Sin verificar.**
