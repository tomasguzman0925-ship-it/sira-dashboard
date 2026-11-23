import datetime as dt

import pandas as pd
import streamlit as st

from comun import encabezado
from datos import actualizacion, clima_observado, corrida, corridas, hoy, pixeles, predio, pronostico, resumen, resumen_de
from estilo import (AGUA, BORDE, PRIMARIO, PRIMARIO_CLARO, ROJO, SOL, SUAVE, TARJETA, TEXTO, fecha_corta, kpi,
                    mini, num, tabla_simple, titulo_panel)

encabezado("Datos y modelo")
RIEGO = {"CD": "Cascada", "MIRI": "MIRI", "AWD+MIRI": "AWD + MIRI"}

R, p, obs = resumen(), predio(), clima_observado()
H = hoy()
emision = dt.date.fromisoformat(pronostico().emision.iloc[0])
ult = obs.fecha.max().date()
reciente = obs[obs.fecha >= obs.fecha.max() - pd.Timedelta(days=120)]
prov = reciente[reciente.fuente_lluvia != "CHIRPS"]
desde_prov = prov.fecha.min().date() if len(prov) else None
rev = actualizacion()
revisado = dt.datetime.fromisoformat(rev["revisado"]) if rev else None


def fecha_txt(d: dt.date) -> str:
    return f"{fecha_corta(d)} {d.year}"


ETAPAS = [
    ("Fuentes abiertas", AGUA, ["Sentinel-2 y Landsat (Planetary Computer)", "Lluvia CHIRPS y NASA POWER",
                                "Pronóstico NASA GEOS-S2S", "198 mediciones TDR de Nataima"]),
    ("Ingesta", AGUA, ["Python en el equipo: imágenes, clima y GEOS-S2S", "subir_aws.py → S3",
                       "AWS Lambda: clima diario en la tabla Iceberg clima_dia"]),
    ("Lakehouse en S3", SOL, ["Bronce: tal como llega", "Plata: limpio, por pixel y día", "Oro: listo para decidir",
                              "Parquet (Snappy) y JSON"]),
    ("Procesamiento", SOL, ["EventBridge, 5:00 a. m. → Step Functions", "Glue sira-b-02 (PySpark): clima y GEOS-S2S",
                            "Glue sira-b-05: modelos y semáforo"]),
    ("Modelos", PRIMARIO, ["A · Random Forest: NDVI y NDMI a 30 días", "B · ARIMAX(1): humedad de hoy",
                           "FAO-56 con 5 escenarios: de hoy a 30 días", "Alarma del NDMI"]),
    ("Consumo", PRIMARIO, ["Athena: 13 tablas", "API en AWS Lambda → app Lovable", "Este tablero"]),
]


def diagrama() -> str:
    tarjetas = []
    for n, (titulo, color, items) in enumerate(ETAPAS, 1):
        lineas = "".join(f"<div style='margin-top:0.25rem'>{t}</div>" for t in items)
        tarjetas.append(
            f"<div style='flex:1 1 150px;min-width:150px;background:{TARJETA};border:1px solid {BORDE};border-top:4px solid {color};"
            f"border-radius:10px;padding:0.6rem 0.75rem'><div style='font-size:0.75rem;font-weight:600;color:{color}'>{n}</div>"
            f"<div style='font-weight:600;color:{TEXTO}'>{titulo}</div>"
            f"<div style='font-size:0.82rem;color:{SUAVE};line-height:1.3'>{lineas}</div></div>")
    flecha = f"<div style='align-self:center;color:{SUAVE};font-size:1.3rem;flex:none'>›</div>"
    return f"<div style='display:flex;flex-wrap:wrap;gap:0.45rem;align-items:stretch'>{flecha.join(tarjetas)}</div>"


def modo(texto: str, fondo: str, color: str) -> str:
    return (f"<span style='background:{fondo};color:{color};border-radius:999px;padding:0.1rem 0.55rem;font-size:0.8rem;"
            f"font-weight:600;white-space:nowrap'>{texto}</span>")


AUTO = modo("Automático", PRIMARIO_CLARO, PRIMARIO)
EQUIPO = modo("Lo sube el equipo", "#FBEBD8", SOL)

PROCESOS = [
    ("Datos nuevos", "actualizar_datos.py y bajar_geos.py traen imágenes, lluvia y GEOS-S2S; subir_aws.py los sube a S3",
     "Cuando el equipo los sube", f"Lluvia hasta el {fecha_txt(H)}", EQUIPO),
    ("Clima y pronóstico corregido", "Glue sira-b-02 (PySpark): clima desde 2001 y corrección del sesgo de GEOS-S2S",
     "Cada 5 días y cada mes", f"Emisión del {fecha_txt(emision)}", AUTO),
    ("Semáforo por pixel", f"Glue sira-b-05: modelos A y B y FAO-56 sobre {num(len(pixeles()))} pixeles → S3 (oro) y Athena",
     "Cada día, 5:00 a. m.", f"Emisión del {fecha_txt(H)}", AUTO),
    ("Consulta y app", "Athena (13 tablas) y API en AWS Lambda (sira-b-api-serving) → app Lovable", "Al consultar",
     f"Emisión del {fecha_txt(H)}", AUTO),
    ("Este tablero", "GitHub Actions trae la última emisión y el clima del día (reglas de clima_dia) → Streamlit",
     "Cada día, 5:30 a. m.", f"{fecha_txt(revisado.date())}, {revisado:%H:%M}" if revisado else "—", AUTO),
]


def tabla_procesos() -> str:
    cab = "".join(f"<th style='text-align:left;padding:0.45rem 0.6rem;color:{SUAVE};font-weight:600;font-size:0.8rem;"
                  f"border-bottom:1px solid {BORDE}'>{t}</th>" for t in ("Proceso", "Herramientas", "Cada cuánto", "Último dato", ""))
    filas = "".join(
        "<tr>" + "".join(f"<td style='padding:0.5rem 0.6rem;border-bottom:1px solid {BORDE};vertical-align:top;"
                         f"{'font-weight:600;' if i == 0 else ''}{'color:' + SUAVE + ';' if i == 1 else ''}'>{v}</td>"
                         for i, v in enumerate(fila)) + "</tr>" for fila in PROCESOS)
    return (f"<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:0.88rem'>"
            f"<tr>{cab}</tr>{filas}</table></div>")


with st.container(border=True):
    titulo_panel("Cómo llegan los datos")
    st.markdown(diagrama(), unsafe_allow_html=True)
    st.write("")
    st.markdown(tabla_procesos(), unsafe_allow_html=True)
    if desde_prov:
        st.markdown(f"<div class='nota'>La lluvia desde el {fecha_corta(desde_prov)} es provisional (Open-Meteo): CHIRPS "
                    f"publica con unas 7 semanas de atraso y la reemplaza cuando sale.</div>", unsafe_allow_html=True)

st.write("")
a, b = st.columns([1, 2], gap="medium")
with a:
    with st.container(border=True):
        titulo_panel("Volumen")
        mini([
            ("Pixeles de 10 m por corrida", num(len(pixeles()))), ("Días de clima desde 1981", num(len(obs))),
            ("Pronóstico por corrida", f"{R['miembros_geos']} × 30 días"), ("Corridas guardadas", num(len(corridas()))),
        ])
with b:
    with st.container(border=True):
        titulo_panel("Historial de corridas")
        filas = []
        for c in reversed(corridas()):
            r0 = resumen_de(c)["horizontes"][0]
            hueco = resumen_de(c).get("lluvia_hueco") or {}
            filas.append({
                "Corrida": fecha_txt(dt.date.fromisoformat(c)), "": "● en pantalla" if c == corrida() else "",
                "Arroz": f"{num(r0['ha_en_cultivo'], 1)} ha", "Suficiente": f"{num(r0['suficiente']['pct'], 1)} %",
                "Regar pronto": f"{num(r0['media']['pct'], 1)} %", "Regar ya": f"{num(r0['baja']['pct'], 1)} %",
                "Agua que falta": f"{num(r0['media']['agua_m3_zona'] + r0['baja']['agua_m3_zona'])} m³",
                "Lluvia sin CHIRPS": f"NASA POWER, {hueco['dias_sin_chirps']} días" if hueco.get("relleno") == "power" else "0 mm",
            })
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
        st.markdown("<div class='nota'>Para ver otra corrida, cambia la fecha del semáforo en la barra lateral.</div>",
                    unsafe_allow_html=True)

st.write("")
titulo_panel("Qué tan confiable es")
c = st.columns(4)
kpi(c[0], "Rojos detectados", "9 de 17", "en la prueba con mediciones reales (TDR), con el margen de hoy", PRIMARIO, PRIMARIO)
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
            ("Riego hasta hoy", f"{RIEGO.get(R['modelo_b']['riego_supuesto'].split()[0], 'Cascada')}, promedio de 3 temporadas medidas"),
            ("Riego desde hoy", "Ninguno: el mapa muestra cuándo hace falta"),
            ("Margen de seguridad hoy", f"{num(R['modelo_b']['margen_mm'], 2)} mm: el error típico de B "
                                        f"({num(R['modelo_b']['sigma_pct'], 2)} %) en lámina; solo hoy"),
            ("Lluvia y ETo futuras", f"Promedio de {R['miembros_geos']} escenarios de GEOS-S2S"),
            *([("Lluvia sin CHIRPS", f"NASA POWER en los últimos {hueco['dias_sin_chirps']} días")]
              if (hueco := R.get("lluvia_hueco")) and hueco.get("relleno") == "power" else []),
            ("Humedad de hoy", "ARIMAX(1) entrenado con 198 mediciones TDR"),
            ("NDVI y NDMI futuros", "Random Forest, 10 años de Sentinel-2 y Landsat"),
            ("Humedad de hoy a 30 días", "Balance hídrico FAO-56"),
        ])

st.markdown(f"<div class='nota'>SIRA · Equipo 10, Maestría en Ciencia de Datos y Analítica, Universidad EAFIT. "
            f"Código y reportes: <a href='https://github.com/GomSal/SIRA'>github.com/GomSal/SIRA</a>.</div>", unsafe_allow_html=True)
