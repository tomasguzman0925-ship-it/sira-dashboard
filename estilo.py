"""Identidad visual y componentes de interfaz del tablero operativo."""

import datetime as dt

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

FONDO = "#F4F6F3"
TARJETA = "#FFFFFF"
BORDE = "#E1E5DF"
TEXTO = "#17201B"
SUAVE = "#66716A"
PRIMARIO = "#1F6F43"
PRIMARIO_CLARO = "#E3F0E7"
AGUA = "#2F6FA3"
AGUA_CLARO = "#CFE1F0"
SOL = "#C9772B"
REJILLA = "#E7EAE5"

ROJO = "#D6453D"
AMBAR = "#F0A830"
VERDE = "#2E9E5B"
MORADO = "#7C5CC4"
GRIS = "#B7BEB8"

ESTADOS = {2: ("Regar ya", ROJO), 1: ("Regar pronto", AMBAR), 0: ("Suficiente", VERDE), 3: ("Revisar en campo", MORADO)}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

_t = go.layout.Template()
_t.layout = go.Layout(
    font=dict(family="IBM Plex Sans, Arial, sans-serif", size=13, color=TEXTO),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[PRIMARIO, AGUA, AMBAR, ROJO, MORADO, GRIS],
    xaxis=dict(gridcolor=REJILLA, linecolor=BORDE, zeroline=False, ticks="", title=dict(font=dict(size=12, color=SUAVE))),
    yaxis=dict(gridcolor=REJILLA, linecolor=BORDE, zeroline=False, title=dict(font=dict(size=12, color=SUAVE))),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor=TARJETA, bordercolor=BORDE, font=dict(family="IBM Plex Sans, Arial, sans-serif", size=13, color=TEXTO)),
    margin=dict(l=8, r=8, t=28, b=8),
)
pio.templates["sira"] = _t
pio.templates.default = "sira"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html, body, .stMarkdown p, .stMarkdown li, .stCaption, label p, button p {{ font-family: 'IBM Plex Sans', Arial, sans-serif; }}
h1, h2, h3, h4 {{ font-family: 'IBM Plex Sans', Arial, sans-serif !important; font-weight: 600 !important; color: {TEXTO}; letter-spacing: -0.2px; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 4.2rem; padding-bottom: 2rem; max-width: 1480px; }}
[data-testid="stSidebar"] {{ background: {TARJETA}; border-right: 1px solid {BORDE}; }}
.cab {{ display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 0.6rem; margin-bottom: 0.6rem; }}
.cab h1 {{ font-size: 1.65rem; margin: 0; padding: 0; }}
.cab .sub {{ color: {SUAVE}; font-size: 0.95rem; margin-top: 0.1rem; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
.chip {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 999px; padding: 0.2rem 0.7rem; font-size: 0.82rem; color: {SUAVE}; white-space: nowrap; }}
.chip b {{ color: {TEXTO}; font-weight: 600; }}
.kpi {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px; padding: 0.85rem 1rem 0.8rem; height: 100%;
        box-shadow: 0 1px 2px rgba(23,32,27,0.04); }}
.kpi .t {{ display: flex; align-items: center; gap: 0.45rem; font-size: 0.8rem; font-weight: 600; color: {SUAVE}; text-transform: uppercase; letter-spacing: 0.4px; }}
.kpi .t i {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }}
.kpi .v {{ font-size: 1.85rem; font-weight: 700; line-height: 1.15; margin-top: 0.3rem; font-variant-numeric: tabular-nums; }}
.kpi .d {{ font-size: 0.86rem; color: {SUAVE}; margin-top: 0.15rem; }}
.panel-t {{ font-size: 0.95rem; font-weight: 600; color: {TEXTO}; margin: 0.2rem 0 0.4rem; }}
.prio {{ display: flex; align-items: center; gap: 0.7rem; padding: 0.55rem 0.2rem; border-bottom: 1px solid {BORDE}; }}
.prio:last-child {{ border-bottom: none; }}
.prio .n {{ font-weight: 700; min-width: 3.1rem; }}
.prio .x {{ flex: 1; font-size: 0.86rem; color: {SUAVE}; line-height: 1.3; }}
.prio .x b {{ color: {TEXTO}; font-weight: 600; }}
.badge {{ display: inline-block; border-radius: 6px; padding: 0.12rem 0.5rem; font-size: 0.78rem; font-weight: 600; color: #fff; white-space: nowrap; }}
.ley {{ display: flex; flex-wrap: wrap; gap: 0.9rem; font-size: 0.85rem; color: {SUAVE}; margin-top: 0.3rem; }}
.ley span {{ display: inline-flex; align-items: center; gap: 0.35rem; }}
.ley i {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
.grad {{ height: 10px; border-radius: 5px; margin-top: 0.4rem; }}
.grad-l {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: {SUAVE}; }}
.nota {{ font-size: 0.8rem; color: {SUAVE}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: {TARJETA}; }}
</style>
"""


def aplicar_estilo() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def fecha_corta(d: dt.date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


def fecha_larga(d: dt.date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def num(x: float, dec: int = 0) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def cabecera(titulo: str, sub: str, chips: list[str]) -> None:
    html_chips = "".join(f'<span class="chip">{c}</span>' for c in chips)
    st.markdown(f'<div class="cab"><div><h1>{titulo}</h1><div class="sub">{sub}</div></div>'
                f'<div class="chips">{html_chips}</div></div>', unsafe_allow_html=True)


def kpi(col, titulo: str, valor: str, detalle: str, color: str = TEXTO, punto: str | None = None) -> None:
    p = f'<i style="background:{punto}"></i>' if punto else ""
    col.markdown(f'<div class="kpi"><div class="t">{p}{titulo}</div><div class="v" style="color:{color}">{valor}</div>'
                 f'<div class="d">{detalle}</div></div>', unsafe_allow_html=True)


def badge(texto: str, color: str) -> str:
    return f'<span class="badge" style="background:{color}">{texto}</span>'


def leyenda(items: list[tuple[str, str]]) -> None:
    st.markdown('<div class="ley">' + "".join(f'<span><i style="background:{c}"></i>{t}</span>' for t, c in items) + "</div>",
                unsafe_allow_html=True)


def leyenda_gradiente(colores: list[str], izq: str, der: str, titulo: str) -> None:
    st.markdown(f'<div class="nota">{titulo}</div><div class="grad" style="background:linear-gradient(90deg,{",".join(colores)})"></div>'
                f'<div class="grad-l"><span>{izq}</span><span>{der}</span></div>', unsafe_allow_html=True)


def mini(items: list[tuple[str, str]]) -> None:
    """Rejilla de 2 columnas con cifras pequeñas: (etiqueta, valor)."""
    celdas = "".join(f"<div><div class='nota'>{e}</div><div style='font-size:1.35rem;font-weight:700'>{v}</div></div>" for e, v in items)
    st.markdown(f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.6rem 1rem;margin-bottom:0.4rem'>{celdas}</div>",
                unsafe_allow_html=True)


def tabla_simple(filas: list[tuple[str, str]]) -> None:
    html = "".join(f"<tr><td style='padding:0.4rem 0.6rem;color:{SUAVE};border-bottom:1px solid {BORDE}'>{a}</td>"
                   f"<td style='padding:0.4rem 0.6rem;font-weight:500;border-bottom:1px solid {BORDE}'>{b}</td></tr>" for a, b in filas)
    st.markdown(f"<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>{html}</table>", unsafe_allow_html=True)


def ejes_fecha(fig: go.Figure, fechas, paso: int = 3) -> None:
    fechas = list(fechas)[::paso]
    fig.update_xaxes(tickvals=fechas, ticktext=[fecha_corta(pd_fecha(f)) for f in fechas])


def pd_fecha(f) -> dt.date:
    return f.date() if hasattr(f, "date") and not isinstance(f, dt.date) else (f if isinstance(f, dt.date) else dt.date.fromisoformat(str(f)[:10]))


def titulo_panel(texto: str) -> None:
    st.markdown(f'<div class="panel-t">{texto}</div>', unsafe_allow_html=True)


def mostrar(fig: go.Figure, alto: int = 320, clave: str | None = None) -> None:
    fig.update_layout(height=alto)
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "locale": "es",
                                                  "modeBarButtonsToRemove": ["select2d", "lasso2d"]}, key=clave)
