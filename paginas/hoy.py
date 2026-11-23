import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from comun import encabezado, fecha_horizonte, figura_mapa
from datos import hoy, lotes, pixeles, pronostico, resumen
from estilo import (AGUA, AMBAR, BORDE, MORADO, ROJO, SUAVE, TEXTO, VERDE, badge, fecha_corta, fecha_larga, kpi, leyenda, mostrar,
                    num, titulo_panel)

encabezado("Situación de riego")

R, L, px = resumen(), lotes(), pixeles()
h0 = R["horizontes"][0]
cult = px[px.clase_h0 >= 0]
limite = L.loc[L.accion == "Programar riego", "fecha_limite"].min()
alerta_ha = cult.marca_h0.sum() / 100

c = st.columns(4)
kpi(c[0], "Regar hoy", f"{num(h0['baja']['ha'], 1)} ha", f"{num(h0['baja']['agua_m3_zona'])} m³ para volver a capacidad de campo", ROJO, ROJO)
kpi(c[1], f"Regar antes del {fecha_corta(limite)}", f"{num(h0['media']['ha'], 1)} ha",
    f"pasan a «regar ya» en {h0['media']['dias_hasta_baja_mediana']} días si no se riega", "#A86A00", AMBAR)
kpi(c[2], "Con agua suficiente", f"{num(h0['suficiente']['ha'], 1)} ha", f"{num(h0['suficiente']['pct'], 0)} % del arroz", VERDE, VERDE)
kpi(c[3], "Revisar en campo", f"{num(alerta_ha, 1)} ha", "NDMI fuera de lo normal: posible enfermedad o deficiencia nutricional", MORADO, MORADO)

st.write("")
izq, der = st.columns([1.75, 1], gap="medium")
with izq:
    with st.container(border=True):
        titulo_panel("Estado de riego hoy")
        mostrar(figura_mapa("Estado de riego", 0), 520, clave="mapa_hoy")
        leyenda([("Regar ya", ROJO), ("Regar pronto", AMBAR), ("Suficiente", VERDE), ("Revisar en campo", MORADO)])
with der:
    with st.container(border=True, height=600):
        titulo_panel("Prioridades por lote")
        colores = {"Regar hoy": ROJO, "Regar en 1–2 días": AMBAR, "Programar riego": AGUA, "Sin riego por ahora": VERDE}
        filas = []
        for r in L.itertuples():
            cuando = "hoy" if r.accion == "Regar hoy" else (f"antes del {fecha_corta(r.fecha_limite)}" if r.fecha_limite else "—")
            filas.append(f'<div class="prio"><div class="n">{r.lote}</div><div class="x"><b>{num(r.area_ha, 1)} ha</b> · '
                         f'{num(r.agua_hoy_m3)} m³ hoy · {r.etapa.lower()}<br>{num(100 * r.pct_rojo)} % en rojo · regar {cuando}</div>'
                         f'{badge(r.accion, colores[r.accion])}</div>')
        st.markdown("".join(filas), unsafe_allow_html=True)

st.write("")
a, b = st.columns([1.75, 1], gap="medium")
with a:
    with st.container(border=True):
        titulo_panel("Próximos 7 días")
        f = pronostico().head(7)
        cols = st.columns(7)
        for col, r in zip(cols, f.itertuples()):
            icono = "rainy" if r.lluvia >= 5 else ("partly_cloudy_day" if r.lluvia >= 1 else "sunny")
            color = AGUA if r.lluvia >= 1 else "#C9772B"
            col.markdown(f"<div style='text-align:center'><div style='font-size:0.85rem;color:{SUAVE}'>{fecha_larga(r.fecha)}</div>"
                         f"<div style='font-family:\"Material Symbols Rounded\";font-size:2rem;color:{color};line-height:1.3'>{icono}</div>"
                         f"<div style='font-weight:700;font-size:1.05rem'>{num(r.lluvia, 1)} mm</div>"
                         f"<div style='font-size:0.8rem;color:{SUAVE}'>ETo {num(r.eto, 1)} mm</div>"
                         f"<div style='font-size:0.8rem;color:{SUAVE}'>{num(r.tmin, 0)}–{num(r.tmax, 0)} °C</div></div>",
                         unsafe_allow_html=True)
        st.markdown(f"<div class='nota' style='margin-top:0.5rem'>Lluvia media de 5 escenarios del pronóstico; ETo = agua que pide la "
                    f"atmósfera. Semana: lluvia {num(f.lluvia.sum(), 0)} mm frente a ETo {num(f.eto.sum(), 0)} mm.</div>",
                    unsafe_allow_html=True)
with b:
    with st.container(border=True):
        titulo_panel("Si no se riega")
        fig = go.Figure()
        hs = R["horizontes"]
        etiquetas = [fecha_horizonte(x["h"]) for x in hs]
        for clave, nombre, color in (("baja", "Regar ya", ROJO), ("media", "Regar pronto", AMBAR), ("suficiente", "Suficiente", VERDE)):
            vals = [x[clave]["pct"] for x in hs]
            fig.add_trace(go.Bar(x=etiquetas, y=vals, name=nombre, marker_color=color,
                                 text=[f"{v:.0f}%" if v >= 9 else "" for v in vals], textposition="inside",
                                 hovertemplate="%{x}: %{y:.1f} %<extra>" + nombre + "</extra>"))
        fig.update_layout(barmode="stack", yaxis=dict(title="% del arroz", range=[0, 100]), showlegend=False, bargap=0.35)
        mostrar(fig, 215, clave="sin_riego")
