import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import encabezado
from datos import curva_normal, lotes, pixeles
from estilo import AGUA, MORADO, PRIMARIO, ROJO, SOL, SUAVE, VERDE, kpi, mostrar, num, titulo_panel

encabezado("Estado del cultivo")

px, L, cn = pixeles(), lotes(), curva_normal()
cult = px[px.clase_h0 >= 0]
bajo = (cult.vigor_z < -1).mean()
etapa_dom = L.groupby("etapa").area_ha.sum().idxmax()
das_dom = L.groupby("das").area_ha.sum().idxmax()

c = st.columns(4)
kpi(c[0], "Arroz en la zona", f"{num(len(cult) / 100, 1)} ha", f"{len(L)} lotes de 0,5 ha o más", PRIMARIO, PRIMARIO)
kpi(c[1], "Etapa predominante", etapa_dom, f"{int(das_dom)} días desde la siembra", PRIMARIO, VERDE)
kpi(c[2], "Vigor bajo", f"{num(100 * bajo, 0)} %", "del arroz con NDVI bajo lo normal para su edad", SOL, SOL)
kpi(c[3], "Revisar en campo", f"{num(cult.marca_h0.sum() / 100, 2)} ha", f"en {(L.alertas_px > 0).sum()} lotes", MORADO, MORADO)

st.write("")
a, b = st.columns([1.5, 1], gap="medium")
with a:
    with st.container(border=True):
        titulo_panel("Vigor de cada lote frente a la curva normal del arroz (10 años)")
        fig = go.Figure()
        x = cn.das_centro
        fig.add_trace(go.Scatter(x=list(x) + list(x[::-1]), y=list(cn.ndvi0_mean + cn.ndvi0_std) + list((cn.ndvi0_mean - cn.ndvi0_std)[::-1]),
                                 fill="toself", fillcolor="rgba(46,158,91,0.12)", line=dict(width=0), name="Rango normal", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=cn.ndvi0_mean, mode="lines", line=dict(color=VERDE, width=2, dash="dot"), name="Normal",
                                 hovertemplate="Día %{x:.0f}: NDVI normal %{y:.2f}<extra></extra>"))
        colores = {"Bajo": SOL, "Normal": PRIMARIO, "Alto": AGUA}
        for v, g in L.groupby("vigor"):
            fig.add_trace(go.Scatter(x=g.das, y=g.ndvi, mode="markers" if v == "Normal" else "markers+text", text=g.lote,
                                     textposition="middle right", name=f"Vigor {v.lower()}", textfont=dict(size=12, color=SUAVE),
                                     marker=dict(size=(g.area_ha.clip(0.5) ** 0.5) * 9, color=colores[v], line=dict(color="#FFFFFF", width=1.5)),
                                     customdata=list(zip(g.area_ha, g.ndvi_normal)),
                                     hovertemplate="%{text}: %{x:.0f} días · NDVI %{y:.2f} (normal %{customdata[1]:.2f}) · %{customdata[0]:.1f} ha<extra></extra>"))
        fig.update_layout(xaxis=dict(title="Días desde la siembra", range=[0, 155]), yaxis=dict(title="NDVI", range=[0, 1]))
        mostrar(fig, 380, clave="vigor")
with b:
    with st.container(border=True):
        titulo_panel("Área por etapa")
        orden = ["Vegetativa", "Reproductiva", "Maduración", "Cosecha / socas"]
        e = L.groupby("etapa").area_ha.sum().reindex(orden).fillna(0)
        fig = go.Figure(go.Bar(x=e.values, y=e.index, orientation="h", marker_color=["#8BC48A", PRIMARIO, "#C9A24A", "#B7BEB8"],
                               text=[f"{num(v, 1)} ha" for v in e.values], textposition="outside"))
        fig.update_layout(xaxis=dict(visible=False, range=[0, e.max() * 1.3]), yaxis=dict(autorange="reversed"), showlegend=False)
        mostrar(fig, 170, clave="etapas")
        titulo_panel("Revisar en campo")
        al = cult[cult.marca_h0].groupby("lote").agg(area_m2=("pixel", "count"), lat=("lat", "mean"), lon=("lon", "mean")).reset_index()
        al["area_m2"] = al.area_m2 * 100
        al = al.sort_values("area_m2", ascending=False)
        al["mapa"] = [f"https://www.google.com/maps?q={la:.5f},{lo:.5f}" for la, lo in zip(al.lat, al.lon)]
        st.dataframe(al[["lote", "area_m2", "mapa"]], hide_index=True, width="stretch", height=180,
                     column_config={"lote": "Lote", "area_m2": st.column_config.NumberColumn("Área (m²)", format="%d"),
                                    "mapa": st.column_config.LinkColumn("Ubicación", display_text="Abrir mapa")})

with st.container(border=True):
    titulo_panel("Lotes")
    t = L[["lote", "siembra", "das", "etapa", "area_ha", "ndvi", "ndvi_normal", "vigor", "ndvi_30d", "ndmi", "alertas_px"]].copy()
    t["siembra"] = pd.to_datetime(t.siembra)
    t["tendencia"] = t.ndvi_30d - t.ndvi
    t["alertas_px"] = t.alertas_px * 100
    st.dataframe(t.drop(columns="ndvi_30d").sort_values("lote"), hide_index=True, width="stretch",
                 column_config={"lote": "Lote", "siembra": st.column_config.DateColumn("Siembra estimada", format="DD/MM/YYYY"),
                                "das": st.column_config.NumberColumn("Días", format="%d"), "etapa": "Etapa",
                                "area_ha": st.column_config.NumberColumn("Área (ha)", format="%.1f"),
                                "ndvi": st.column_config.NumberColumn("NDVI hoy", format="%.2f"),
                                "ndvi_normal": st.column_config.NumberColumn("NDVI normal", format="%.2f"),
                                "vigor": "Vigor", "tendencia": st.column_config.NumberColumn("Cambio NDVI a 30 días", format="%+.2f"),
                                "ndmi": st.column_config.NumberColumn("NDMI hoy", format="%.2f"),
                                "alertas_px": st.column_config.NumberColumn("Revisar (m²)", format="%d")})
    st.markdown("<div class='nota'>Siembra detectada con la curva del NDVI de Sentinel-2 y Landsat. Pronóstico del NDVI a 30 días: modelo A (Random Forest).</div>",
                unsafe_allow_html=True)
