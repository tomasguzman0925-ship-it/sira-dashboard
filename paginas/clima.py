import datetime as dt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import encabezado
from datos import clima_observado, hoy, pronostico, pronostico_miembros
from estilo import AGUA, AGUA_CLARO, ROJO, SOL, SUAVE, TEXTO, ejes_fecha, fecha_corta, kpi, mostrar, num, titulo_panel

encabezado("Clima y balance de agua")

f, m, obs = pronostico(), pronostico_miembros(), clima_observado()
H = hoy()
s7, s30 = f.head(7), f
miembros7 = m[m.fecha < H + dt.timedelta(days=7)].groupby("miembro").lluvia_corr_mm.sum()
base = obs[(obs.fecha.dt.year >= 1991) & (obs.fecha.dt.year <= 2020)]
dias_rango = pd.date_range(H, periods=len(s30)).strftime("%m-%d")
normal = base[base.fecha.dt.strftime("%m-%d").isin(dias_rango)].groupby(base.fecha.dt.year).lluvia_mm.sum().mean()

c = st.columns(4)
kpi(c[0], "Lluvia próximos 7 días", f"{num(s7.lluvia.sum())} mm", f"rango de escenarios {num(miembros7.min())}–{num(miembros7.max())} mm", AGUA, AGUA)
kpi(c[1], "ETo próximos 7 días", f"{num(s7.eto.sum())} mm", "agua que piden el cultivo y la atmósfera", SOL, SOL)
bal = s7.lluvia.sum() - s7.eto.sum()
kpi(c[2], "Balance 7 días", f"{'+' if bal >= 0 else '−'}{num(abs(bal))} mm", "déficit: el suelo se seca" if bal < 0 else "excedente",
    ROJO if bal < 0 else AGUA, ROJO if bal < 0 else AGUA)
kpi(c[3], f"Lluvia próximos {len(s30)} días", f"{num(s30.lluvia.sum())} mm",
    f"lo normal (1991–2020) es {num(normal)} mm", AGUA, AGUA)

st.write("")
with st.container(border=True):
    titulo_panel("Pronóstico diario · GEOS-S2S de la NASA, 5 escenarios corregidos para Nataima")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=f.fecha, y=f.lluvia, name="Lluvia (media)", marker_color=AGUA,
                         error_y=dict(type="data", symmetric=False, array=f.lluvia_max - f.lluvia, arrayminus=f.lluvia - f.lluvia_min,
                                      color="#8AA9C4", thickness=1.2, width=3),
                         hovertemplate="%{x|%d %b}: %{y:.1f} mm<extra>lluvia</extra>"))
    fig.add_trace(go.Scatter(x=f.fecha, y=f.eto, name="ETo", mode="lines", line=dict(color=SOL, width=2.5),
                             hovertemplate="%{x|%d %b}: %{y:.1f} mm<extra>ETo</extra>"))
    fig.update_layout(yaxis_title="mm por día", bargap=0.25)
    ejes_fecha(fig, f.fecha, 3)
    mostrar(fig, 330, clave="diario")

a, b = st.columns([1.3, 1], gap="medium")
with a:
    with st.container(border=True):
        titulo_panel("Balance acumulado: lluvia − ETo")
        fig = go.Figure()
        for k, g in m.sort_values("fecha").groupby("miembro"):
            fig.add_trace(go.Scatter(x=g.fecha, y=(g.lluvia_corr_mm - g.eto_corr_mm).cumsum(), mode="lines", line=dict(color="#B9C7D3", width=1.5),
                                     showlegend=bool(k == m.miembro.min()), name="Cada escenario", legendgroup="e",
                                     hovertemplate="%{x|%d %b}: %{y:.0f} mm<extra>escenario " + str(k) + "</extra>"))
        fig.add_trace(go.Scatter(x=f.fecha, y=(f.lluvia - f.eto).cumsum(), mode="lines", line=dict(color=AGUA, width=3.5), name="Media",
                                 hovertemplate="%{x|%d %b}: %{y:.0f} mm<extra>media</extra>"))
        fig.add_hline(y=0, line=dict(color=TEXTO, width=1))
        fig.update_layout(yaxis_title="mm acumulados")
        ejes_fecha(fig, f.fecha, 5)
        mostrar(fig, 300, clave="balance")
with b:
    with st.container(border=True):
        titulo_panel("Resumen semanal")
        f2 = f.copy()
        f2["semana"] = (pd.to_datetime(f2.fecha) - pd.Timestamp(H)).dt.days // 7 + 1
        sem = f2[f2.semana <= 4].groupby("semana").agg(desde=("fecha", "min"), hasta=("fecha", "max"), lluvia=("lluvia", "sum"),
                                                       eto=("eto", "sum")).reset_index()
        sem["balance"] = sem.lluvia - sem.eto
        sem["Semana"] = [f"{fecha_corta(a)} – {fecha_corta(b)}" for a, b in zip(sem.desde, sem.hasta)]
        st.dataframe(sem[["Semana", "lluvia", "eto", "balance"]], hide_index=True, width="stretch",
                     column_config={"lluvia": st.column_config.NumberColumn("Lluvia (mm)", format="%.0f"),
                                    "eto": st.column_config.NumberColumn("ETo (mm)", format="%.0f"),
                                    "balance": st.column_config.NumberColumn("Balance (mm)", format="%+.0f")})
        st.markdown("<div class='nota'>Balance negativo: el arroz consume más agua de la que llueve.</div>", unsafe_allow_html=True)

with st.container(border=True):
    titulo_panel("Últimos 60 días observados")
    o = obs[obs.fecha >= obs.fecha.max() - pd.Timedelta(days=59)]
    prov = o.fuente_lluvia.ne("CHIRPS")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=o.fecha, y=o.lluvia_mm, name="Lluvia", marker_color=np.where(prov, AGUA_CLARO, AGUA),
                         customdata=o.fuente_lluvia, hovertemplate="%{x|%d %b}: %{y:.1f} mm · %{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=o.fecha, y=o.eto_mm, name="ETo", mode="lines", line=dict(color=SOL, width=2)))
    fig.update_layout(yaxis_title="mm por día", bargap=0.2)
    ejes_fecha(fig, o.fecha, 6)
    mostrar(fig, 280, clave="observado")
    st.markdown(f"<div class='nota'>Lluvia CHIRPS y ETo FAO-56 con NASA POWER. Barras claras: dato provisional de Open-Meteo mientras "
                f"llega CHIRPS ({prov.sum()} de {len(o)} días). Último día: {fecha_corta(o.fecha.max().date())}.</div>",
                unsafe_allow_html=True)
