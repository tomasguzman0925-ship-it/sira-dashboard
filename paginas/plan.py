import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import encabezado
from datos import hoy, lotes, pixeles, resumen
from estilo import AGUA, AMBAR, BORDE, ROJO, SUAVE, VERDE, fecha_corta, kpi, mostrar, num, titulo_panel

encabezado("Plan de riego por lote")

L, R, px = lotes(), resumen(), pixeles()
H = hoy()
hz = {x["h"]: x for x in R["horizontes"]}
agua_hoy = hz[0]["media"]["agua_m3_zona"] + hz[0]["baja"]["agua_m3_zona"]
agua_7 = hz[7]["baja"]["agua_m3_zona"] + hz[7]["media"]["agua_m3_zona"]

c = st.columns(4)
kpi(c[0], "Lotes a regar hoy", str((L.accion == "Regar hoy").sum()), f"de {len(L)} lotes detectados", ROJO, ROJO)
kpi(c[1], "Fecha límite del resto", fecha_corta(L.loc[L.accion != "Regar hoy", "fecha_limite"].min()),
    "antes de pasar a «regar ya»", "#A86A00", AMBAR)
kpi(c[2], "Agua si se riega hoy", f"{num(agua_hoy)} m³", f"toda la zona · {num(agua_hoy / max(hz[0]['ha_en_cultivo'], 1), 0)} m³/ha", AGUA, AGUA)
kpi(c[3], "Agua si se espera 7 días", f"{num(agua_7)} m³", f"{num(agua_7 / agua_hoy, 1)} veces más que hoy", ROJO, ROJO)

st.write("")
with st.container(border=True):
    titulo_panel("Calendario de los próximos 14 días")
    dias = 14
    fig = go.Figure()
    orden = L.lote.tolist()[::-1]
    for r in L.itertuples():
        if r.accion == "Regar hoy":
            tramos = [(0, 1, "Regar", ROJO), (1, dias, "En déficit si no se riega", "#F2C9C5")]
        else:
            lim = (r.fecha_limite - H).days
            tramos = [(0, lim, "Con agua", "#CFE8D7"), (lim, lim + 1, "Regar", AMBAR), (lim + 1, dias, "En déficit si no se riega", "#F2C9C5")]
        for ini, fin, nombre, color in tramos:
            if fin <= ini:
                continue
            fig.add_trace(go.Bar(y=[r.lote], x=[fin - ini], base=[ini], orientation="h", marker=dict(color=color, line=dict(color="#FFFFFF", width=1)),
                                 name=nombre, legendgroup=nombre, showlegend=False,
                                 hovertemplate=f"{r.lote} · {nombre}<br>{fecha_corta(H + dt.timedelta(days=ini))} → "
                                               f"{fecha_corta(H + dt.timedelta(days=fin - 1))}<extra></extra>"))
    for nombre, color in (("Con agua", "#CFE8D7"), ("Día de riego", AMBAR), ("Regar hoy", ROJO), ("En déficit si no se riega", "#F2C9C5")):
        fig.add_trace(go.Bar(y=[None], x=[None], name=nombre, marker_color=color))
    ticks = list(range(0, dias + 1, 1))
    fig.update_layout(barmode="overlay", yaxis=dict(categoryorder="array", categoryarray=orden),
                      xaxis=dict(tickvals=[t + 0.5 for t in ticks[:-1]], ticktext=[fecha_corta(H + dt.timedelta(days=t)) for t in ticks[:-1]],
                                 range=[0, dias], showgrid=False),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), bargap=0.25)
    fig.add_vline(x=0, line=dict(color="#17201B", width=2))
    mostrar(fig, 430, clave="calendario")

with st.container(border=True):
    titulo_panel("Detalle por lote")
    t = L[["lote", "accion", "fecha_limite", "area_ha", "etapa", "das", "pct_rojo", "humedad_pct", "lamina_mm", "agua_hoy_m3", "agua_7d_m3", "alertas_px"]].copy()
    t["fecha_limite"] = pd.to_datetime(t.fecha_limite)
    t["pct_rojo"] = 100 * t.pct_rojo
    t["alertas_px"] = t.alertas_px / 100
    st.dataframe(
        t, hide_index=True, width="stretch",
        column_config={
            "lote": st.column_config.TextColumn("Lote", width="small"),
            "accion": st.column_config.TextColumn("Acción"),
            "fecha_limite": st.column_config.DateColumn("Regar a más tardar", format="DD/MM/YYYY"),
            "area_ha": st.column_config.NumberColumn("Área (ha)", format="%.1f"),
            "etapa": st.column_config.TextColumn("Etapa"),
            "das": st.column_config.NumberColumn("Días de siembra", format="%d"),
            "pct_rojo": st.column_config.ProgressColumn("% en rojo hoy", min_value=0, max_value=100, format="%.0f %%"),
            "humedad_pct": st.column_config.NumberColumn("Humedad (%)", format="%.1f"),
            "lamina_mm": st.column_config.NumberColumn("Lámina hoy (mm)", format="%.1f", help="1 mm = 1 L/m² = 10 m³/ha"),
            "agua_hoy_m3": st.column_config.NumberColumn("Agua hoy (m³)", format="%.0f"),
            "agua_7d_m3": st.column_config.NumberColumn("Agua en 7 días (m³)", format="%.0f"),
            "alertas_px": st.column_config.NumberColumn("Revisar en campo (ha)", format="%.2f"),
        })
    disperso = px[(px.clase_h0 >= 0) & (px.lote == "Disperso")]
    st.markdown(f"<div class='nota'>Lotes = áreas continuas de arroz con la misma fecha de siembra, de 0,5 ha o más. "
                f"Fuera de lotes quedan {num(len(disperso) / 100, 1)} ha dispersas ({num(disperso.agua_m3_h0.sum())} m³ hoy).</div>",
                unsafe_allow_html=True)
    st.download_button("Descargar plan (CSV)", t.to_csv(index=False).encode("utf-8"), f"plan_riego_{H.isoformat()}.csv", "text/csv",
                       icon=":material/download:")
