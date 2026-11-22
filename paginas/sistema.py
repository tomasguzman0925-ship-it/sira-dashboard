import datetime as dt

import pandas as pd
import streamlit as st

from comun import encabezado
from datos import clima_observado, hoy, predio, pronostico, resumen
from estilo import AGUA, PRIMARIO, ROJO, SOL, SUAVE, fecha_corta, kpi, num, tabla_simple, titulo_panel

encabezado("Datos y modelo")

R, p, obs = resumen(), predio(), clima_observado()
H = hoy()
emision = dt.date.fromisoformat(pronostico().emision.iloc[0])
ult = obs.fecha.max().date()
reciente = obs[obs.fecha >= obs.fecha.max() - pd.Timedelta(days=120)]
prov = reciente[reciente.fuente_lluvia != "CHIRPS"]
desde_prov = prov.fecha.min().date() if len(prov) else None

with st.container(border=True):
    titulo_panel("Estado de los datos")
    st.dataframe(pd.DataFrame([
        ("Semáforo por pixel", f"{fecha_corta(H)} {H.year}, 5:00 a. m.", "Cada día, 5:00 a. m.", "20.286 pixeles de 10 m"),
        ("Pronóstico del clima (NASA GEOS-S2S)", f"Emisión del {fecha_corta(emision)} {emision.year}", "Cada 5 días", "5 escenarios, 30 días, corregido para el sitio"),
        ("Lluvia y ETo observadas (CHIRPS, NASA POWER)", f"{fecha_corta(ult)} {ult.year}", "Cada día",
         f"Lluvia provisional (Open-Meteo) desde el {fecha_corta(desde_prov)}" if desde_prov else "Definitiva"),
        ("Imágenes Sentinel-2 y Landsat", "Hasta la última corrida", "Cada 2–5 días según nubes", "Huecos por nubes rellenados con Prithvi-EO-2.0"),
    ], columns=["Fuente", "Último dato", "Actualización", "Nota"]), hide_index=True, width="stretch")

st.write("")
titulo_panel("Qué tan confiable es")
c = st.columns(4)
kpi(c[0], "Suelos secos detectados", "12 de 17", "en la prueba con mediciones reales (TDR)", PRIMARIO, PRIMARIO)
kpi(c[1], "Error típico de humedad", f"± {num(R['modelo_b']['sigma_pct'], 1)} %", "≈ 4,7 L/m² por pixel, hoy", SOL, SOL)
kpi(c[2], "Pronóstico del vigor (NDVI)", "28 % mejor", "que repetir la última imagen; 32 % a 30 días", AGUA, AGUA)
kpi(c[3], "Precisión del rojo hoy", "1 de 5", "rojos del día 0 confirmados: verificar antes de regar", ROJO, ROJO)

st.write("")
a, b = st.columns(2, gap="medium")
with a:
    with st.container(border=True):
        titulo_panel("Suelo del predio")
        tabla_simple([
            ("Capacidad de campo", f"{num(p.fc_pct)} %"), ("Punto de marchitez", f"{num(p.pwp_pct)} %"),
            ("Umbral «regar ya»", f"{num(p.umbral_rojo_pct, 1)} % · déficit de {num(p.dr_rojo_mm, 2)} mm"),
            ("Profundidad de raíz", f"{num(p.zr_mm)} mm"), ("Agua útil (TAW)", f"{num(p.taw_mm, 1)} mm"),
            ("Agotamiento permitido (p)", num(p.p_agotamiento, 2)),
        ])
        st.markdown("<div class='nota'>Calibrado con el ensayo de Agrosavia en el C.I. Nataima (Martínez-Vega et al., 2025). "
                    "Otros suelos requieren calibración con sensores.</div>", unsafe_allow_html=True)
with b:
    with st.container(border=True):
        titulo_panel("Supuestos de la corrida")
        tabla_simple([
            ("Riego hasta hoy", "Cascada, promedio de 3 temporadas medidas"),
            ("Riego desde hoy", "Ninguno: el mapa muestra cuándo hace falta"),
            ("Margen de seguridad hoy", f"{num(R['modelo_b']['margen_mm'], 2)} mm (1,5 veces el error típico)"),
            ("Lluvia y ETo futuras", f"Promedio de {R['miembros_geos']} escenarios de GEOS-S2S"),
            ("Humedad de hoy", "ARIMAX(1) entrenado con 198 mediciones TDR"),
            ("NDVI y NDMI futuros", "Random Forest, 10 años de Sentinel-2 y Landsat"),
            ("Humedad de hoy a 30 días", "Balance hídrico FAO-56"),
        ])

st.markdown(f"<div class='nota'>SIRA · Equipo 10, Maestría en Ciencia de Datos y Analítica, Universidad EAFIT. "
            f"Código y reportes: <a href='https://github.com/GomSal/SIRA'>github.com/GomSal/SIRA</a>.</div>", unsafe_allow_html=True)
