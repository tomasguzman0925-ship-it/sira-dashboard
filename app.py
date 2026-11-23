"""SIRA · tablero operativo de riego de arroz.

Ejecutar:  streamlit run app.py
"""

import datetime as dt

import streamlit as st

from datos import corrida_para, corridas, vigilar_datos
from estilo import AMBAR, MORADO, PRIMARIO, ROJO, SUAVE, VERDE, aplicar_estilo, fecha_corta

st.set_page_config(page_title="SIRA · Riego de arroz", page_icon="💧", layout="wide")
vigilar_datos()
aplicar_estilo()

with st.sidebar:
    st.markdown(f"<div style='font-size:1.5rem;font-weight:700;color:{PRIMARIO}'>SIRA</div>"
                f"<div style='color:{SUAVE};font-size:0.9rem;margin-top:-0.2rem'>Riego de arroz por pixel</div>",
                unsafe_allow_html=True)
    st.selectbox("Predio", ["C.I. Nataima · zona 2 × 2 km"], key="predio")
    lista = corridas()
    primera, ultima = dt.date.fromisoformat(lista[0]), dt.date.fromisoformat(lista[-1])
    tope = max(ultima, dt.date.today())
    if "fecha" not in st.session_state:
        try:
            pedida = dt.date.fromisoformat(st.query_params.get("fecha", ""))
        except ValueError:
            pedida = ultima
        st.session_state["fecha"] = min(max(pedida, primera), tope)
    fecha = st.date_input("Fecha del semáforo", min_value=primera, max_value=tope, format="DD/MM/YYYY", key="fecha")
    st.session_state["corrida"] = corrida_para(fecha)
    mostrada = dt.date.fromisoformat(st.session_state["corrida"])
    if mostrada != fecha:
        st.caption(f"No hay corrida del {fecha_corta(fecha)}: se muestra la del {fecha_corta(mostrada)}.")
    st.caption(f"{len(lista)} corridas guardadas, del {fecha_corta(primera)} {primera.year} "
               f"al {fecha_corta(ultima)} {ultima.year}.")
    st.markdown("**Colores del semáforo**")
    for nombre, color, que in (("Regar ya", ROJO, "humedad bajo 27,1 %"), ("Regar pronto", AMBAR, "entre 27,1 y 30 %"),
                               ("Suficiente", VERDE, "30 % o más"), ("Revisar en campo", MORADO, "posible plaga o deficiencia")):
        st.markdown(f"<div style='display:flex;gap:0.5rem;align-items:center;margin:0.25rem 0'>"
                    f"<span style='width:12px;height:12px;border-radius:3px;background:{color};flex:none'></span>"
                    f"<span style='font-size:0.88rem'><b>{nombre}</b> <span style='color:{SUAVE}'>· {que}</span></span></div>",
                    unsafe_allow_html=True)
    st.caption("Escenario: sin riego desde la última actualización. 1 mm = 1 L/m² = 10 m³/ha.")

paginas = [
    st.Page("paginas/hoy.py", title="Hoy", icon=":material/today:", default=True),
    st.Page("paginas/mapa.py", title="Mapa", icon=":material/map:"),
    st.Page("paginas/plan.py", title="Plan de riego", icon=":material/water_drop:"),
    st.Page("paginas/clima.py", title="Clima", icon=":material/partly_cloudy_day:"),
    st.Page("paginas/cultivo.py", title="Cultivo", icon=":material/grass:"),
    st.Page("paginas/sistema.py", title="Datos y modelo", icon=":material/monitoring:"),
]
st.navigation(paginas, position="top").run()
