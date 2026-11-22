"""SIRA · tablero operativo de riego de arroz.

Ejecutar:  streamlit run app.py
"""

import streamlit as st

from estilo import AMBAR, MORADO, PRIMARIO, ROJO, SUAVE, VERDE, aplicar_estilo

st.set_page_config(page_title="SIRA · Riego de arroz", page_icon="💧", layout="wide")
aplicar_estilo()

with st.sidebar:
    st.markdown(f"<div style='font-size:1.5rem;font-weight:700;color:{PRIMARIO}'>SIRA</div>"
                f"<div style='color:{SUAVE};font-size:0.9rem;margin-top:-0.2rem'>Riego de arroz por pixel</div>",
                unsafe_allow_html=True)
    st.selectbox("Predio", ["C.I. Nataima · zona 2 × 2 km"], key="predio")
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
