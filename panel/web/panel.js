"use strict";
// MaesTrials — panel. Todo el texto se pinta con textContent (nunca HTML), así ningún pie puede inyectar código.

const numero = new Intl.NumberFormat("es-ES", { useGrouping: "always" });   // "3.120", no "3120"
const fechaCorta = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });
const fechaHora = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const contenido = document.getElementById("contenido");
const VISTAS = { versiones: vistaVersiones, ganadores: vistaGanadores, resultados: vistaResultados };
const ORDENES = {
  retencion: (a, b) => (b.retencion ?? 0) - (a.retencion ?? 0),
  visitas: (a, b) => b.visitas - a.visitas,
  disponibles: (a, b) => (b.disponible - a.disponible) || ((b.retencion ?? 0) - (a.retencion ?? 0)),
};

/* ---------- utilidades ---------- */
function el(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined && texto !== null) nodo.textContent = texto;
  return nodo;
}
function con(padre, ...hijos) { hijos.filter(Boolean).forEach((h) => padre.append(h)); return padre; }
function porcentaje(x) { return x == null ? "—" : `${Math.round(x * 100)} %`; }
function hace(iso) {
  const horas = (Date.now() - new Date(iso)) / 36e5;
  if (horas < 1) return "hace menos de 1 h";
  if (horas < 24) return `hace ${Math.round(horas)} h`;
  return `hace ${Math.round(horas / 24)} días`;
}
function guardar(clave, valor) { try { localStorage.setItem(clave, valor); } catch { /* sin almacenamiento: no pasa nada */ } }
function leer(clave, defecto) { try { return localStorage.getItem(clave) || defecto; } catch { return defecto; } }

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`/api/panel?r=${ruta}`, { credentials: "same-origin", ...opciones });
  if (r.status === 401) { location.href = "/entrar.html"; throw new Error("Hace falta entrar"); }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.error || `Error ${r.status}`);
  return datos;
}

/* ---------- piezas comunes ---------- */
function titular(titulo, texto, extra) {
  const caja = el("section", "titular");
  return con(caja, con(el("div"), el("h1", null, titulo), el("p", null, texto)), extra);
}
function cifra(valor, texto, destacada = false) {
  return con(el("div", destacada ? "cifra destacada" : "cifra"), el("strong", null, valor), el("span", null, texto));
}
function dato(valor, texto) { return con(el("div"), el("strong", null, valor), el("span", null, texto)); }
function portada(miniatura, enlace) {
  const a = el("a", "portada");
  a.href = enlace || "#";
  a.target = "_blank";
  a.rel = "noopener";
  a.title = "Abrir en Instagram";
  if (miniatura) {
    const img = el("img");
    img.src = miniatura;
    img.alt = "";
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    a.append(img);
  }
  return a;
}
function cargando(cuantos) {
  const rejilla = el("div", "rejilla");
  for (let i = 0; i < cuantos; i++) rejilla.append(el("div", "esqueleto"));
  contenido.replaceChildren(rejilla);
}
function mostrarError(error, reintentar) {
  const caja = con(el("div", "aviso error"), el("p", null, `No se pudieron cargar los datos: ${error.message}`));
  const boton = el("button", "boton", "Reintentar");
  boton.addEventListener("click", reintentar);
  contenido.replaceChildren(con(caja, boton));
}

/* ---------- Ganadores ---------- */
function tarjetaGanador(g, puesto) {
  const tarjeta = el("article", g.disponible ? "tarjeta" : "tarjeta en-espera");
  const foto = portada(g.miniatura, g.enlace);
  const barra = el("div", "barra-retencion");
  const relleno = el("b");
  relleno.style.width = `${Math.min(100, Math.round((g.retencion ?? 0) * 100))}%`;
  con(barra, el("small", null, `${porcentaje(g.retencion)} visto`), con(el("i"), relleno));
  foto.append(barra);

  const estado = g.disponible
    ? el("span", "estado ok", "Disponible")
    : el("span", "estado espera", `Vuelve el ${fechaCorta.format(new Date(g.disponible_desde))}`);
  const cuerpo = con(el("div", "cuerpo"),
    el("p", "titulo", g.titulo || "Sin pie"),
    con(el("div", "datos"),
      dato(numero.format(g.visitas), "visitas"),
      dato(g.publicaciones, "publicaciones")),
    con(el("div", "pie-tarjeta"), estado,
      el("span", "nota", `${g.duracion_s ? `${Math.round(g.duracion_s)} s · ` : ""}última ${hace(g.ultima)}`)));
  return con(tarjeta, el("span", "puesto", `#${puesto}`), g.manual ? el("span", "chip-manual", "A mano") : null, foto, cuerpo);
}

async function vistaGanadores() {
  cargando(8);
  let datos;
  try { datos = await pedir("ganadores"); } catch (e) { return mostrarError(e, vistaGanadores); }
  const lista = datos.ganadores;
  const orden = leer("mt_orden", "retencion");

  const selector = el("select");
  [["retencion", "Retención"], ["visitas", "Visitas"], ["disponibles", "Disponibles primero"]].forEach(([valor, texto]) => {
    const opcion = el("option", null, texto);
    opcion.value = valor;
    opcion.selected = valor === orden;
    selector.append(opcion);
  });
  selector.addEventListener("change", () => { guardar("mt_orden", selector.value); pintar(); });

  const rejilla = el("div", "rejilla");
  function pintar() {
    const ordenados = [...lista].sort(ORDENES[selector.value] || ORDENES.retencion);
    rejilla.replaceChildren(...ordenados.map((g, i) => tarjetaGanador(g, i + 1)));
  }
  pintar();

  const disponibles = lista.filter((g) => g.disponible).length;
  const corte = datos.corte ? numero.format(Math.round(datos.corte)) : "—";

  const anadir = el("form", "anadir");
  const enlace = el("input");
  enlace.type = "url";
  enlace.required = true;
  enlace.placeholder = "Pega el enlace de un reel tuyo para añadirlo como ganador";
  const botonAnadir = el("button", "boton", "Añadir ganador");
  botonAnadir.type = "submit";
  anadir.addEventListener("submit", (evento) => {
    evento.preventDefault();
    accion(botonAnadir, "Añadiendo…", () => enviar("anadir", { enlace: enlace.value }),
      (r) => `Añadido como ganador: ${r.pie || r.mejor_id}`, vistaGanadores);
  });
  con(anadir, enlace, botonAnadir);

  contenido.replaceChildren(
    titular("Ganadores",
      `Tus vídeos en el 20 % con más visitas (más de ${corte}), más los que añadas a mano. El orden por retención es la prioridad: es lo que más separa a un ganador de un vídeo flojo.`,
      con(el("label", "orden"), el("span", null, "Ordenar por"), selector)),
    con(el("section", "titular"), anadir),
    con(el("section", "resumen"),
      cifra(disponibles, "disponibles para publicar hoy", true),
      cifra(lista.length, "ganadores"),
      cifra(corte, "visitas de corte (top 20 %)"),
      cifra(`${datos.dias_minimos} días`, "entre publicaciones del mismo vídeo")),
    rejilla);
}

/* ---------- Resultados ---------- */
function filaResultado(p, horasResultado) {
  const titulo = p.gancho || p.titulo || "Trial";
  const texto = con(el("div", "fila-texto"),
    el("p", "titulo", titulo),
    p.gancho ? el("span", "gancho", p.titulo) : null,
    el("span", "nota", `Publicado el ${fechaHora.format(new Date(p.publicado_en))} · ${hace(p.publicado_en)}`
      + (p.medido_en ? ` · medido ${hace(p.medido_en)}` : " · sin medir todavía")),
    con(el("div", "metricas"),
      dato(numero.format(p.alcance), "alcance"),
      dato(porcentaje(p.retencion), "retención"),
      dato(numero.format(p.compartidos), "compartidos"),
      dato(numero.format(p.guardados), "guardados"),
      dato(numero.format(p.comentarios), "comentarios")));

  let estado;
  if (p.foto_24h && p.visitas === 0) estado = el("span", "estado malo", "Se quedó en 0");
  else if (p.foto_24h) estado = el("span", "estado ok", `Foto de las ${p.horas_medida} h`);
  else if (p.cumplio_24h) estado = el("span", "estado espera", "24 h cumplidas · falta la foto");
  else estado = el("span", "estado neutro", `Midiendo · ${Math.floor(p.horas)}/${horasResultado} h`);
  const barra = el("div", "progreso");
  const relleno = el("b");
  relleno.style.width = `${Math.min(100, Math.round((p.horas / horasResultado) * 100))}%`;
  barra.append(relleno);
  const grande = con(el("div", "grande"), el("strong", null, numero.format(p.visitas)), el("span", null, "visitas"), estado,
    p.cumplio_24h ? null : barra);
  return con(el("article", "fila"), portada(p.miniatura, p.enlace), texto, grande);
}

async function vistaResultados() {
  cargando(3);
  let datos;
  try { datos = await pedir("resultados"); } catch (e) { return mostrarError(e, vistaResultados); }
  const lista = datos.publicaciones;
  const medidos = lista.filter((p) => p.cumplio_24h);
  const enCero = medidos.filter((p) => p.foto_24h && p.visitas === 0).length;
  const total = lista.reduce((suma, p) => suma + p.visitas, 0);
  const conRetencion = lista.filter((p) => p.retencion != null);
  const retencionMedia = conRetencion.length
    ? conRetencion.reduce((s, p) => s + p.retencion, 0) / conRetencion.length : null;

  const cuerpo = lista.length
    ? con(el("section", "lista"), ...lista.map((p) => filaResultado(p, datos.horas_resultado)))
    : el("div", "aviso", "Todavía no hay trials publicados por MaesTrials.");
  contenido.replaceChildren(
    titular("Resultados",
      `Cada trial publicado por MaesTrials. El dato que cuenta es a las ${datos.horas_resultado} h; Instagram puede tardar hasta 48 h en dar las métricas.`),
    con(el("section", "resumen"),
      cifra(numero.format(total), "visitas de todos los trials", true),
      cifra(lista.length, "trials publicados"),
      cifra(medidos.length ? `${enCero} de ${medidos.length}` : "—", "se quedaron en 0 (objetivo < 10 %)"),
      cifra(porcentaje(retencionMedia), "retención media")),
    cuerpo);
}

/* ---------- avisos y acciones ---------- */
let temporizadorAviso;
function avisar(texto, esError = false) {
  const caja = document.getElementById("aviso");
  caja.textContent = texto;
  caja.className = esError ? "aviso-flotante error" : "aviso-flotante";
  caja.hidden = false;
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => { caja.hidden = true; }, esError ? 10000 : 5000);
}
function enviar(ruta, cuerpo = {}) {
  return pedir(ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
}
async function conBoton(boton, textoEspera, tarea) {
  const original = boton.textContent;
  boton.disabled = true;
  boton.textContent = textoEspera;
  try { return await tarea(); } finally { boton.disabled = false; boton.textContent = original; }
}
async function accion(boton, espera, tarea, mensaje, despues) {
  try {
    const resultado = await conBoton(boton, espera, tarea);
    avisar(mensaje(resultado));
    despues();
  } catch (e) {
    avisar(e.message, true);
  }
}
function pintarAutopilot(encendido) {
  const caja = document.getElementById("autopilot");
  caja.checked = Boolean(encendido);
  caja.disabled = false;
  document.getElementById("autopilot-texto").textContent = encendido ? "Autopilot encendido" : "Autopilot apagado";
}

/* ---------- Versiones ---------- */
function tarjetaVersion(v, orden) {
  const video = el("video");
  video.src = v.video;
  video.controls = true;
  video.preload = "metadata";
  video.playsInline = true;
  const texto = el("div", "version-texto");

  function botones() {
    const publicar = el("button", "boton", "Publicar ahora");
    const editar = el("button", "boton-suave", "Editar");
    const rehacer = el("button", "boton-suave", "Rehacer");
    rehacer.title = "Claude escribe otro gancho y otro pie, y se monta de nuevo";
    const descartar = el("button", "boton-suave peligro", "Descartar");
    publicar.addEventListener("click", () => {
      if (!confirm(`¿Publicar AHORA en tu Instagram como trial?\n\nGancho: ${v.gancho.join(" ")}\n\nPie:\n${v.pie}`)) return;
      accion(publicar, "Publicando… (1-2 min)", () => enviar("publicar", { archivo: v.archivo }),
        (r) => `Publicado como trial: ${r.enlace || r.publicacion}`, vistaVersiones);
    });
    editar.addEventListener("click", formulario);
    rehacer.addEventListener("click", () => {
      if (!confirm("¿Rehacer esta versión? Claude escribe otro gancho y otro pie y se monta de nuevo (30-90 s).")) return;
      accion(rehacer, "Rehaciendo…", () => enviar("rehacer", { archivo: v.archivo }), () => "Versión rehecha y subida", vistaVersiones);
    });
    descartar.addEventListener("click", () => {
      if (!confirm("¿Descartar esta versión? Se borra y no se publicará.")) return;
      accion(descartar, "Descartando…", () => enviar("descartar", { archivo: v.archivo }), () => "Versión descartada", vistaVersiones);
    });
    return con(el("div", "acciones"), publicar, editar, rehacer, descartar);
  }
  function vista() {
    texto.replaceChildren(
      el("span", "orden-cola", orden === 1 ? "Sale la siguiente" : `${orden}.ª en la cola`),
      el("p", "titulo", v.titulo || v.origen),
      el("div", "gancho-caja", v.gancho.join("\n")),
      el("p", "pie-texto", v.pie),
      el("span", "palabra", `Palabra clave: ${v.palabra}`),
      botones());
  }
  function formulario() {
    const form = el("form", "formulario-edicion");
    const gancho = el("input");
    gancho.value = v.gancho.join(" ");
    gancho.maxLength = 44;
    const pie = el("textarea");
    pie.value = v.pie;
    pie.maxLength = 2200;
    const guardarBoton = el("button", "boton", "Guardar y volver a montar");
    guardarBoton.type = "submit";
    const cancelar = el("button", "boton-suave", "Cancelar");
    cancelar.type = "button";
    cancelar.addEventListener("click", vista);
    form.addEventListener("submit", (evento) => {
      evento.preventDefault();
      accion(guardarBoton, "Montando y subiendo…",
        () => enviar("editar", { archivo: v.archivo, gancho: gancho.value, pie: pie.value }),
        () => "Versión editada y subida", vistaVersiones);
    });
    texto.replaceChildren(con(form,
      el("label", null, "Gancho en pantalla (2 líneas de 22 letras como mucho)"), gancho,
      el("label", null, `Pie (tiene que llevar ${v.palabra})`), pie,
      con(el("div", "acciones"), guardarBoton, cancelar)));
  }
  vista();
  return con(el("article", "version"), video, texto);
}

function filaPublicada(p) {
  const visitas = p.visitas_24h != null ? `${numero.format(p.visitas_24h)} visitas a las 24 h`
    : p.visitas != null ? `${numero.format(p.visitas)} visitas hasta ahora` : "sin medir";
  let enlace = null;
  if (p.enlace) {
    enlace = el("a", null, "Ver en Instagram");
    enlace.href = p.enlace;
    enlace.target = "_blank";
    enlace.rel = "noopener";
  }
  return con(el("article", "publicada"),
    con(el("div", "fila-texto"),
      el("p", "titulo", p.gancho.length ? p.gancho.join(" ") : p.titulo),
      el("span", "nota", `${fechaHora.format(new Date(p.publicado_en))} · ${hace(p.publicado_en)}`)),
    con(el("div", "publicada-datos"), el("strong", null, visitas), enlace));
}

async function vistaVersiones() {
  cargando(3);
  let datos;
  try { datos = await pedir("versiones"); } catch (e) { return mostrarError(e, vistaVersiones); }
  pintarAutopilot(datos.autopilot);
  const proximo = datos.proximo_hueco ? fechaHora.format(new Date(datos.proximo_hueco)) : "—";
  const con24 = datos.publicadas.filter((p) => p.visitas_24h != null);
  const media24 = con24.length ? numero.format(Math.round(con24.reduce((s, p) => s + p.visitas_24h, 0) / con24.length)) : "—";
  const huecos = datos.huecos_ny.map((h) => `${h}:00`).join(", ");
  const cola = datos.cola.length
    ? con(el("section", "cola"), ...datos.cola.map((v, i) => tarjetaVersion(v, i + 1)))
    : el("div", "aviso", "No hay versiones en cola. GitHub prepara las del día a las 11:05 UTC.");
  contenido.replaceChildren(
    titular("Versiones", datos.autopilot
      ? `El autopilot publica la primera de la cola en cada hueco: ${huecos} (hora de Nueva York).`
      : "El autopilot está apagado: no se publica nada solo. Puedes publicar a mano con «Publicar ahora»."),
    con(el("section", "resumen"),
      cifra(datos.cola.length, "versiones en cola", true),
      cifra(datos.autopilot ? proximo : "Apagado", "próxima publicación (tu hora)"),
      cifra(datos.publicadas.length, "trials publicados"),
      cifra(media24, "visitas a las 24 h (media)")),
    el("h2", "seccion-titulo", "En cola"), cola,
    el("h2", "seccion-titulo", "Publicadas"), con(el("section", "publicadas"), ...datos.publicadas.map(filaPublicada)));
}

/* ---------- navegación ---------- */
function irA(vista) {
  const nombre = VISTAS[vista] ? vista : "versiones";
  document.querySelectorAll(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.vista === nombre));
  if (location.hash !== `#${nombre}`) history.replaceState(null, "", `#${nombre}`);
  window.scrollTo(0, 0);
  VISTAS[nombre]();
}
document.querySelectorAll(".pestanas button").forEach((b) => b.addEventListener("click", () => irA(b.dataset.vista)));
document.getElementById("autopilot").addEventListener("change", async (evento) => {
  const caja = evento.target;
  const quiere = caja.checked;
  const pregunta = quiere ? "¿Encender el autopilot? GitHub publicará solo en los huecos."
    : "¿Apagar el autopilot? No se publicará nada solo hasta que lo enciendas.";
  if (!confirm(pregunta)) { caja.checked = !quiere; return; }
  caja.disabled = true;
  try {
    const ajustes = await enviar("autopilot", { encendido: quiere });
    pintarAutopilot(ajustes.autopilot);
    avisar(ajustes.autopilot ? "Autopilot encendido y guardado en GitHub" : "Autopilot apagado y guardado en GitHub");
    if (location.hash === "#versiones") vistaVersiones();
  } catch (e) {
    caja.checked = !quiere;
    caja.disabled = false;
    avisar(e.message, true);
  }
});
document.getElementById("sincronizar").addEventListener("click", (evento) => {
  const boton = evento.currentTarget;
  accion(boton, "Sincronizando…", () => enviar("sincronizar"), () => "Datos al día con GitHub",
    () => irA(location.hash.slice(1)));
});
window.addEventListener("hashchange", () => irA(location.hash.slice(1)));

(async function arrancar() {
  try { await enviar("sincronizar"); } catch (e) { avisar(`No se pudo sincronizar con GitHub: ${e.message}`, true); }
  irA(location.hash.slice(1));
})();
