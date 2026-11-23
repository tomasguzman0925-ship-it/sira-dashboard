"""Cómo se entrenaron los modelos A y B: flujo de entrenamiento y gráficas de evaluación.

Los datos de evaluación son fijos (salen del entrenamiento, no de la corrida diaria) y viven en modelos/,
copiados de los reportes de github.com/GomSal/SIRA:
  a_rmse_prueba.csv       reports/modelo_a/entrenamiento_final/paso8_metricas_absolutas.csv (RMSE por horizonte)
  a_skill_validacion.csv  reports/modelo_a/entrenamiento_final/paso7_validacion.csv (mejor de cada familia)
  b_roc_prueba.csv        reports/semaforo_clasificador_ndvi_prithvi/roc_familias.csv
  b_auc_prueba.csv        reports/semaforo_clasificador_ndvi_prithvi/roc_auc.csv
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from estilo import (AGUA, AMBAR, BORDE, GRIS, PRIMARIO, PRIMARIO_CLARO, ROJO, SOL, SUAVE, TARJETA, TEXTO, VERDE,
                    mostrar, num, titulo_panel)

MOD = Path(__file__).parent / "modelos"


@st.cache_data
def _csv(nombre: str) -> pd.DataFrame:
    return pd.read_csv(MOD / nombre)


# ---------------------------------------------------------------- flujos de entrenamiento
FLUJO_A = [
    ("Entradas", AGUA, ["<b>1.412 imágenes</b> Sentinel-2 y Landsat, 10 m, 2012–2026", "Clima: CHIRPS y NASA POWER",
                        "Nubes: Prithvi-EO-2.0 rellena el pixel"]),
    ("Partición", AGUA, ["Serie de tiempo, ventana deslizante que avanza 1 año", "Entrenar <b>3.652 días</b> (10 años)",
                         "Validar <b>365 días</b>, 3 veces", "Probar <b>316 días</b>, una vez"]),
    ("Métricas", SOL, ["Elige el <b>skill frente a la persistencia</b>: 1 − RMSE / RMSE de repetir el último dato",
                       "Promedio en 1, 3, 7, 15 y 30 días"]),
    ("Estandarización", SOL, ["Media y desviación solo del entrenamiento de cada ventana (ARIMAX y GRU)",
                              "Los árboles no la necesitan"]),
    ("Selección de variables", PRIMARIO, ["Prueba de Diebold–Mariano", "<b>Entran:</b> fenología, NDMI y NDVI (p &lt; 0,005)",
                                          "<b>Salen:</b> lluvia, ETo y Prithvi"]),
    ("Modelos en competencia", PRIMARIO, ["ARIMAX, Random Forest, Gradient Boosting, XGBoost y GRU",
                                          "26 combinaciones de hiperparámetros; gana el mayor skill medio",
                                          "Si el IC 95 % de la diferencia incluye 0, gana el más simple"]),
]
GANA_A = ("Random Forest", ["200 árboles", "NDVI y NDMI a +1–30 días"])

FLUJO_B = [
    ("Entradas", AGUA, ["<b>198 mediciones TDR</b> de humedad en Nataima: 3 temporadas × 3 franjas",
                        "NDVI de Sentinel-2 por franja; HLS → Prithvi", "Clima: CHIRPS y NASA POWER",
                        "Balance FAO-56: S y Dr"]),
    ("Partición", AGUA, ["Bloques de 10 días; las 3 franjas de un bloque van juntas",
                         "Probar en <b>4 particiones</b>: cada medición, una vez", "Validar en <b>5 bloques</b> internos"]),
    ("Métricas", SOL, ["Elige el <b>AUC-ROC macro</b>, fijado antes de ver resultados",
                       "No es un clasificador de etiquetas, sino de umbrales"]),
    ("Estandarización", SOL, ["Media y desviación del entrenamiento (logística y ARIMAX)", "Los árboles no la necesitan"]),
    ("Selección de variables", PRIMARIO, ["<b>Entran:</b> balance S y Dr, riego, ETo y NDVI",
                                          "<b>Salen:</b> Prithvi y NDMI: el IC 95 % de su mejora incluye 0"]),
    ("Modelos en competencia", PRIMARIO, ["Logística, Random Forest, Gradient Boosting, XGBoost y ARIMAX",
                                          "30 combinaciones, con y sin Prithvi; gana el mayor AUC en validación",
                                          "Si el IC 95 % incluye 0, gana el más simple"]),
]
GANA_B = ("ARIMAX", ["7 entradas, sin Prithvi", "Entrega la probabilidad de cada color del semáforo"])


def _flujo(etapas: list, gana: tuple[str, list[str]]) -> str:
    tarjetas = []
    for n, (titulo, color, items) in enumerate(etapas, 1):
        lineas = "".join(f"<div style='margin-top:0.25rem'>{t}</div>" for t in items)
        tarjetas.append(
            f"<div style='flex:1 1 170px;min-width:170px;background:{TARJETA};border:1px solid {BORDE};border-top:4px solid {color};"
            f"border-radius:10px;padding:0.6rem 0.75rem'><div style='font-size:0.75rem;font-weight:600;color:{color}'>{n}</div>"
            f"<div style='font-weight:600;color:{TEXTO}'>{titulo}</div>"
            f"<div style='font-size:0.82rem;color:{SUAVE};line-height:1.3'>{lineas}</div></div>")
    nombre, items = gana
    lineas = "".join(f"<div style='margin-top:0.25rem'>{t}</div>" for t in items)
    tarjetas.append(
        f"<div style='flex:1 1 170px;min-width:170px;background:{PRIMARIO_CLARO};border:2px solid {PRIMARIO};"
        f"border-radius:10px;padding:0.6rem 0.75rem'><div style='font-size:0.75rem;font-weight:600;color:{PRIMARIO}'>Elegido</div>"
        f"<div style='font-weight:700;font-size:1.1rem;color:{PRIMARIO}'>{nombre}</div>"
        f"<div style='font-size:0.82rem;color:{TEXTO};line-height:1.3'>{lineas}</div></div>")
    flecha = f"<div style='align-self:center;color:{SUAVE};font-size:1.3rem;flex:none'>›</div>"
    return f"<div style='display:flex;flex-wrap:wrap;gap:0.45rem;align-items:stretch'>{flecha.join(tarjetas)}</div>"


def _nota(texto: str) -> None:
    st.markdown(f"<div class='nota'>{texto}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- modelo A
def _rmse_horizonte(indice: str) -> go.Figure:
    d = _csv("a_rmse_prueba.csv")
    d = d[d.indice == indice]
    x = [f"{h} d" for h in d.dias]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=d.persistencia, name="Persistencia: repetir el último dato", mode="lines+markers",
                             line=dict(color=GRIS, width=2, dash="dash"), marker=dict(size=8),
                             hovertemplate="%{x}: RMSE %{y:.3f}<extra>Persistencia</extra>"))
    fig.add_trace(go.Scatter(x=x, y=d.modelo, name="Modelo A (Random Forest)", mode="lines+markers+text",
                             line=dict(color=PRIMARIO, width=3), marker=dict(size=9), fill="tonexty",
                             fillcolor="rgba(31,111,67,0.12)",
                             text=[f"−{num(100 * (1 - m / p))} %" for m, p in zip(d.modelo, d.persistencia)],
                             textposition="bottom center", textfont=dict(color=PRIMARIO, size=12),
                             hovertemplate="%{x}: RMSE %{y:.3f} (%{text} de error)<extra>Modelo A</extra>"))
    fig.update_xaxes(title_text="Horizonte del pronóstico")
    fig.update_yaxes(title_text=f"RMSE del {indice.upper()} (menos es mejor)", rangemode="tozero")
    return fig


def _skill_familias(indice: str) -> go.Figure:
    d = _csv("a_skill_validacion.csv")
    d = d[d.indice == indice].sort_values("skill")
    mejor = d.skill.max()
    colores = [PRIMARIO if f == "Random Forest" else (GRIS if e else ROJO) for f, e in zip(d.familia, d.empata)]
    fig = go.Figure(go.Bar(
        y=d.familia, x=d.skill, orientation="h", marker=dict(color=colores), text=[num(s, 3) for s in d.skill],
        textposition="outside", customdata=list(zip(d.ic95_dif_vs_mejor, d.empata.map({True: "empata", False: "pierde"}))),
        hovertemplate="%{y}: skill %{x:.3f}<br>Diferencia con el mejor (IC 95 %): %{customdata[0]}<br>"
                      "%{customdata[1]} con el mejor<extra></extra>"))
    fig.add_vline(x=mejor, line=dict(color=PRIMARIO, width=1.5, dash="dot"))
    fig.update_xaxes(title_text=f"Skill medio en validación ({indice.upper()}) · más es mejor", range=[0, mejor * 1.22])
    fig.update_yaxes(title_text=None)
    return fig


# ---------------------------------------------------------------- modelo B
COLOR_B = {"ARIMAX": PRIMARIO, "Gradient Boosting": AMBAR, "Random Forest": AGUA, "XGBoost": SOL,
           "Regresión logística": GRIS}


def _roc() -> go.Figure:
    r, a = _csv("b_roc_prueba.csv"), _csv("b_auc_prueba.csv").sort_values("auc_macro", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Azar (AUC 0,5)", hoverinfo="skip",
                             line=dict(color=GRIS, width=1.5, dash="dot")))
    for _, f in a.iterrows():
        c = r[r.familia == f.familia]
        gana = f.familia == "ARIMAX"
        fig.add_trace(go.Scatter(x=c.fpr, y=c.tpr, mode="lines", name=f"{f.familia} · {num(f.auc_macro, 2)}",
                                 line=dict(color=COLOR_B.get(f.familia, GRIS), width=4 if gana else 1.8),
                                 opacity=1 if gana else 0.85,
                                 hovertemplate=f"{f.familia}<br>Falsos positivos %{{x:.2f}}<br>Verdaderos positivos %{{y:.2f}}<extra></extra>"))
    fig.update_xaxes(title_text="Tasa de falsos positivos", range=[0, 1], dtick=0.2)
    fig.update_yaxes(title_text="Tasa de verdaderos positivos", range=[0, 1.02], dtick=0.2)
    fig.update_layout(legend=dict(orientation="v", yanchor="bottom", y=0.02, xanchor="right", x=0.99,
                                  bgcolor="rgba(255,255,255,0.85)"))
    return fig


def _auc_ic() -> go.Figure:
    a = _csv("b_auc_prueba.csv").sort_values("auc_macro")
    colores = [PRIMARIO if f == "ARIMAX" else GRIS for f in a.familia]
    fig = go.Figure(go.Bar(
        y=a.familia, x=a.auc_macro - 0.5, base=0.5, orientation="h", marker=dict(color=colores),
        error_x=dict(type="data", symmetric=False, array=a.ic95_alto - a.auc_macro, arrayminus=a.auc_macro - a.ic95_bajo,
                     color=TEXTO, thickness=1.2, width=4),
        text=[num(v, 2) for v in a.auc_macro], textposition="inside", insidetextanchor="start",
        textfont=dict(color="#FFFFFF"),
        customdata=list(zip(a.ic95_bajo, a.ic95_alto)),
        hovertemplate="%{y}: AUC %{text}<br>IC 95 %: %{customdata[0]:.2f}–%{customdata[1]:.2f}<extra></extra>"))
    fig.add_vline(x=0.5, line=dict(color=ROJO, width=1.5))
    fig.update_xaxes(title_text="AUC-ROC macro en la prueba · las barras parten del azar (0,5)", range=[0.5, 0.9])
    fig.update_yaxes(title_text=None)
    return fig


# ---------------------------------------------------------------- sección completa
def seccion_modelos() -> None:
    titulo_panel("Cómo se entrenaron los modelos")
    ta, tb = st.tabs(["Modelo A · pronóstico del cultivo", "Modelo B · humedad de hoy"])
    with ta:
        st.markdown(_flujo(FLUJO_A, GANA_A), unsafe_allow_html=True)
        st.write("")
        indice = st.segmented_control("Índice", ["NDVI", "NDMI"], default="NDVI", key="indice_modelo_a") or "NDVI"
        i = indice.lower()
        a, b = st.columns(2, gap="medium")
        with a:
            with st.container(border=True):
                titulo_panel(f"Error en la prueba (nov 2025 – sep 2026) frente a repetir el último dato")
                mostrar(_rmse_horizonte(i), alto=340, clave=f"a_rmse_{i}")
                _nota("El área verde es el error que el modelo A se ahorra; la ventaja crece con el horizonte. "
                      "A 1 día casi no mejora porque ese error ya es ruido de medición del satélite.")
        with b:
            with st.container(border=True):
                titulo_panel("Elección en validación (nov 2022 – nov 2025)")
                mostrar(_skill_familias(i), alto=340, clave=f"a_skill_{i}")
                _nota("Gris: empata con el mejor (el IC 95 % de la diferencia incluye 0). Rojo: pierde. "
                      "Entre los que empatan gana el más simple: <b>Random Forest</b>.")
    with tb:
        st.markdown(_flujo(FLUJO_B, GANA_B), unsafe_allow_html=True)
        st.write("")
        a, b = st.columns(2, gap="medium")
        with a:
            with st.container(border=True):
                titulo_panel("Curvas ROC en la prueba: 198 mediciones TDR, 5 familias")
                mostrar(_roc(), alto=380, clave="b_roc")
                _nota("Cuanto más arriba y a la izquierda, mejor separa los suelos secos. La diagonal es acertar al azar.")
        with b:
            with st.container(border=True):
                titulo_panel("AUC con su intervalo de confianza (95 %)")
                mostrar(_auc_ic(), alto=380, clave="b_auc")
                _nota("En validación ARIMAX empata con Gradient Boosting + Prithvi (0,774 frente a 0,777) y gana el más "
                      "simple. Con la regla del semáforo (déficit de B + margen) detecta 9 de 17 rojos. "
                      "Prithvi no mejora a B: su vector por bloque de 480 m no distingue las franjas de riego.")
