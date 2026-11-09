"use strict";
// MaesTrials — panel. Todo el texto se pinta con textContent (nunca HTML), así ningún pie puede inyectar código.

const numero = new Intl.NumberFormat("es-ES", { useGrouping: "always" });   // "3.120", no "3120"
const fechaCorta = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });
const fechaHora = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const contenido = document.getElementById("contenido");
const VISTAS = { ganadores: vistaGanadores, resultados: vistaResultados };
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
  return con(tarjeta, el("span", "puesto", `#${puesto}`), foto, cuerpo);
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
  contenido.replaceChildren(
    titular("Ganadores",
      `Tus vídeos en el 20 % con más visitas (más de ${corte}). El orden por retención es la prioridad: es lo que más separa a un ganador de un vídeo flojo.`,
      con(el("label", "orden"), el("span", null, "Ordenar por"), selector)),
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
    el("span", "nota", `Publicado el ${fechaHora.format(new Date(p.publicado_en))} · ${hace(p.publicado_en)}`),
    con(el("div", "metricas"),
      dato(numero.format(p.alcance), "alcance"),
      dato(porcentaje(p.retencion), "retención"),
      dato(numero.format(p.compartidos), "compartidos"),
      dato(numero.format(p.guardados), "guardados"),
      dato(numero.format(p.comentarios), "comentarios")));

  let estado;
  if (!p.cumplio_24h) estado = el("span", "estado neutro", `Midiendo · ${Math.floor(p.horas)}/${horasResultado} h`);
  else if (p.visitas === 0) estado = el("span", "estado malo", "Se quedó en 0");
  else estado = el("span", "estado ok", `${horasResultado} h cumplidas`);
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
  const enCero = medidos.filter((p) => p.visitas === 0).length;
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

/* ---------- navegación ---------- */
function irA(vista) {
  const nombre = VISTAS[vista] ? vista : "ganadores";
  document.querySelectorAll(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.vista === nombre));
  if (location.hash !== `#${nombre}`) history.replaceState(null, "", `#${nombre}`);
  window.scrollTo(0, 0);
  VISTAS[nombre]();
}
document.querySelectorAll(".pestanas button").forEach((b) => b.addEventListener("click", () => irA(b.dataset.vista)));
document.getElementById("salir").addEventListener("click", async () => {
  try { await pedir("salir", { method: "POST" }); } finally { location.href = "/entrar.html"; }
});
window.addEventListener("hashchange", () => irA(location.hash.slice(1)));
irA(location.hash.slice(1));
