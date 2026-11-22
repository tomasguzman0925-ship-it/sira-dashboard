import plotly.graph_objects as go
import streamlit as st

from comun import encabezado, fecha_horizonte, figura_mapa
from datos import CAPAS, HORIZONTES, geojson_prescripcion, lotes, pixeles
from estilo import AMBAR, MORADO, ROJO, VERDE, leyenda, leyenda_gradiente, mini, mostrar, num, titulo_panel

encabezado("Mapa por pixel de 10 m")

px, L = pixeles(), lotes()
t1, t2, t3, t4 = st.columns([1.4, 1.6, 1, 0.8])
capa = t1.selectbox("Capa", list(CAPAS), key="capa")
h = t2.segmented_control("Fecha", HORIZONTES, default=0, format_func=fecha_horizonte, key="h_mapa") or 0
lote = t3.selectbox("Lote", ["Todos"] + sorted(L.lote), key="lote_mapa")
satelite = t4.toggle("Satélite", value=True, key="sat")

sel = px[px[f"clase_h{h}"] >= 0]
if lote != "Todos":
    sel = sel[sel.lote == lote]

izq, der = st.columns([2.6, 1], gap="medium")
with izq:
    with st.container(border=True):
        mostrar(figura_mapa(capa, h, lote, satelite), 640, clave="mapa_grande")
        if CAPAS[capa] is None:
            leyenda([("Regar ya", ROJO), ("Regar pronto", AMBAR), ("Suficiente", VERDE), ("Revisar en campo", MORADO)])
        else:
            col, paradas = CAPAS[capa]
            fin = "30 o más" if col == "dias_hasta_baja" else num(paradas[-1][0], 1)
            leyenda_gradiente([c for _, c in paradas], num(paradas[0][0], 1), fin, capa)

with der:
    with st.container(border=True):
        titulo_panel(f"{'Toda la zona' if lote == 'Todos' else lote} · {fecha_horizonte(h)}")
        area = len(sel) / 100
        agua = sel[f"agua_m3_h{h}"].sum()
        mini([("Área en arroz", f"{num(area, 1)} ha"), ("Agua que falta", f"{num(agua)} m³"),
              ("Humedad media", f"{num(sel[f'humedad_pct_h{h}'].mean(), 1)} %"), ("NDVI medio", num(sel[f"ndvi_h{h}"].mean(), 2))])
        cuenta = sel[f"estado_h{h}"].value_counts()
        nombres = [("Regar ya", 2, ROJO), ("Regar pronto", 1, AMBAR), ("Suficiente", 0, VERDE), ("Revisar", 3, MORADO)]
        fig = go.Figure(go.Bar(y=[n for n, _, _ in nombres], x=[cuenta.get(k, 0) / 100 for _, k, _ in nombres], orientation="h",
                               marker_color=[c for _, _, c in nombres], text=[f"{num(cuenta.get(k, 0) / 100, 1)} ha" for _, k, _ in nombres],
                               textposition="outside", hovertemplate="%{y}: %{x:.1f} ha<extra></extra>"))
        fig.update_layout(xaxis=dict(visible=False, range=[0, max(area, 0.1) * 1.3]), yaxis=dict(autorange="reversed"), showlegend=False)
        mostrar(fig, 190, clave="dist_mapa")
    with st.container(border=True):
        titulo_panel("Mapa de prescripción")
        tabla = sel[["pixel", "lote", "lat", "lon", f"estado_h{h}", f"humedad_pct_h{h}", f"deficit_mm_h{h}", f"agua_m3_h{h}", f"ndvi_h{h}", f"ndmi_h{h}"]].copy()
        tabla.columns = ["pixel", "lote", "lat", "lon", "estado", "humedad_pct", "lamina_mm", "agua_m3", "ndvi", "ndmi"]
        tabla["estado"] = tabla.estado.map({0: "suficiente", 1: "regar pronto", 2: "regar ya", 3: "revisar en campo"})
        tabla["lamina_mm"] = tabla.lamina_mm.clip(lower=0)
        nombre = f"sira_{'zona' if lote == 'Todos' else lote}_{fecha_horizonte(h).replace(' ', '')}"
        st.download_button("CSV por pixel", tabla.to_csv(index=False).encode("utf-8"), f"{nombre}.csv", "text/csv",
                           icon=":material/download:", width="stretch")
        st.download_button("GeoJSON para SIG o maquinaria", geojson_prescripcion(sel, h).encode("utf-8"), f"{nombre}.geojson",
                           "application/geo+json", icon=":material/download:", width="stretch")
        st.caption(f"{num(len(sel))} pixeles de 10 × 10 m con estado, lámina (mm) y volumen (m³).")
