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
- [ ] Clave de la API de Claude en `.env` (`ANTHROPIC_API_KEY`). Hace falta en la Fase 3.

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
- **Percentil 80 = 3.507 visitas → unos 17 ganadores.** Con 10.000 o más visitas: 10 reels; con 20.000 o más: 6.
- 17 ganadores × 3 veces por semana = 51 a la semana ≈ **7 al día** posibles.

---

## 4. Arquitectura (simple)

```
[Vercel Schedules cada 15 min] → función "¿toca publicar?"
        │
        ├─ lee métricas por la API de Instagram → elige ganadores → guarda en la base de datos
        ├─ coge la siguiente versión ya montada (Vercel Blob, URL pública)
        └─ crea el contenedor con trial_params → espera FINISHED → publica → borra el vídeo del Blob

[Montaje de vídeo con ffmpeg]  ← D1: ¿dónde?
   A) GitHub Actions (gratis, ~2.000 min/mes en repo privado): 1 vez al día monta las versiones del día y las sube al Blob. Automático.
   B) Dentro de Vercel: gasta las 4 h de CPU del plan gratis (no da) → obliga a Pro.
   C) En el PC de Jose: gratis, pero el PC tiene que estar encendido.

[Panel web en Vercel]: ganadores, calendario, resultados a 24 h y botón de pausa.
```

Base de datos: una Postgres gratis del Marketplace de Vercel (Neon). Los límites de su plan gratis están **sin verificar**.

---

## 5. Fases (una cada vez y con comprobación)

### Fase 0 — Preparación (con Jose) ✅ HECHA 2026-11-09
- Crear la cuenta de desarrollador de Meta y la app en modo desarrollo, con Instagram Login.
- Dar rol a la cuenta de Instagram de Jose y sacar el token (60 días, renovable).
- **Comprobación:** una llamada a `GET /me/media` devuelve los ~40 reels.

### Fase 1 — Pasada de punta a punta con datos reales (desde el PC) ⏳ PUBLICADO, MIDIENDO
**Resultado (2026-11-09):**
- Ganador: reel `18129515419637342` ("La IA que está cambiando la forma de analizar la bolsa", 119.120 visitas).
- Versión 1 con ffmpeg (`fase1/pasada.py`): zoom 1,10, velocidad 1,05, saturación 1,08 y contraste 1,04. **ffmpeg tardó 4 s** para 56 s de vídeo.
- La API da el vídeo a **720x1280** (ya comprimido por Instagram). Para mejorar la calidad, mejor partir de los archivos originales de Jose.
- URL pública: `https://maestrials.vercel.app/v/<archivo>.mp4` (carpeta `public/v/` del repo).
- **Trial reel publicado:** `18416510161083451` → https://www.instagram.com/reel/DfhVYMrFWa_/ (12:30 UTC). La API aceptó `trial_params` MANUAL y `is_shared_to_feed: false`.
- Pendiente: Jose confirma en la app que sale como "Trial" y medimos las visitas a las 24 h (10-nov, 12:30 UTC).

**Cómo se despliega en Vercel (importante):**
- Solo con commit + push al repo privado `eternitydevzz/maestrials`. Hacerlo desde el panel de Vercel pide un código por email que no llega.
- El autor del commit tiene que ser `eternitydevzz <336098555+eternitydevzz@users.noreply.github.com>` (configurado en este repo). Si no, Vercel marca el despliegue como "Blocked".
- Push con la credencial de gh: `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push`.
- Proyecto Vercel: `info-79696548s-projects/maestrials` (equipo Eternity Group, plan Pro).
- Leer los reels y sus `views` y `comments`, elegir 1 ganador, descargarlo, montar 1 versión con ffmpeg, subirla a una URL pública y publicarla como trial reel `MANUAL`.
- Medir cuánto tarda ffmpeg por versión (sirve para decidir D1).
- **Comprobación:** Jose ve el trial reel en su Instagram y sus visitas a las 24 h.
- **Hasta que Jose no lo vea funcionar, no se construye lo siguiente.**

### Fase 2 — Detector de ganadores
- Percentil 80 + umbral opcional. Lista de ganadores con sus números.
- **Comprobación:** Jose revisa la lista y confirma que son sus mejores reels.

### Fase 3 — Variaciones "de verdad"
- Cada versión cambia varias cosas a la vez: encuadre (zoom/reencuadre distinto), composición (p. ej. vídeo sobre fondo desenfocado), ritmo (empieza en otro momento o lleva otra velocidad), audio (música de fondo o tono), gancho de texto en pantalla y caption reescrito con IA.
- **Hipótesis sin probar:** que esto evite la huella de Instagram. Se mide con el % de versiones en 0 visitas (objetivo < 10 %).
- **Comprobación:** Jose ve 3 versiones y las aprueba a ojo.

### Fase 4 — Publicación automática en Vercel
- Schedules cada 15 min, N al día, separación de 45 min o más, cada vídeo máx. 3 veces por semana.
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
- **R3.** Para 10 trials al día hacen falta unos 24 ganadores (cada vídeo máx. 3 veces por semana). Con el percentil 80 sobre ~40 reels salen unos 8. El umbral fijo y los 2-3 reels de feed nuevos al día deberían subir esa cifra; se comprueba con datos reales en la Fase 2.
- ~~**R4.** El token caduca a los 60 días.~~ Resuelto: el token de usuario del sistema no caduca nunca.
- **R5.** Pasar un trial reel al feed no se elige por API: `MANUAL` (lo pasa Jose) o `SS_PERFORMANCE` (lo pasa Instagram).

## 7. Apuntado para más adelante
- Contenido de IA: comprobar si la API permite marcar la etiqueta "Información de IA" de Meta y si hace falta en estos vídeos. **Sin verificar.**
