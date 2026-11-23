"""Piezas que comparten varias páginas: encabezado del predio y mapa satelital."""

import datetime as dt

import plotly.graph_objects as go

from datos import HORIZONTES, capa_png, corridas, es_ultima, hoy, lotes, pixeles, predio, pronostico, resumen
from estilo import SOL, cabecera, fecha_corta, num

ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def encabezado(titulo: str) -> None:
    p, r = predio(), resumen()
    emision = dt.date.fromisoformat(pronostico().emision.iloc[0])
    historial = [] if es_ultima() else [
        f"<b style='color:{SOL}'>Historial</b> · la más reciente es del {fecha_corta(dt.date.fromisoformat(corridas()[-1]))}"]
    cabecera(titulo, f"C.I. Nataima (Agrosavia) · {p.municipio}, {p.departamento} · distrito de riego {p.distrito_riego}",
             [*historial, f"Semáforo del <b>{fecha_corta(hoy())}</b>", f"Pronóstico NASA del <b>{fecha_corta(emision)}</b>",
              f"<b>{num(r['zona_ha'])} ha</b> · {num(r['horizontes'][0]['ha_en_cultivo'], 1)} ha en arroz"])


def fecha_horizonte(h: int) -> str:
    return "Hoy" if h == 0 else fecha_corta(hoy() + dt.timedelta(days=h))


def figura_mapa(capa: str, h: int, lote: str = "Todos", satelite: bool = True, etiquetas: bool = True) -> go.Figure:
    (lat_s, lon_o), (lat_n, lon_e) = resumen()["limites_latlon"]
    px = pixeles()
    sel = px[px[f"clase_h{h}"] >= 0]
    if lote != "Todos":
        sel = sel[sel.lote == lote]
    fig = go.Figure()
    estado = {0: "Suficiente", 1: "Regar pronto", 2: "Regar ya", 3: "Revisar en campo"}
    fig.add_trace(go.Scattermap(
        lat=sel.lat, lon=sel.lon, mode="markers", marker=dict(size=9, color="rgba(0,0,0,0)"), showlegend=False,
        customdata=list(zip(sel.lote, sel[f"estado_h{h}"].map(estado), sel[f"humedad_pct_h{h}"], sel[f"deficit_mm_h{h}"].clip(lower=0),
                            sel.dias_hasta_baja, sel[f"ndvi_h{h}"])),
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>Humedad %{customdata[2]:.1f} %<br>"
                      "Faltan %{customdata[3]:.1f} L/m²<br>Regar ya en %{customdata[4]} días<br>NDVI %{customdata[5]:.2f}<extra></extra>"))
    L = lotes()
    if etiquetas:
        Lv = L if lote == "Todos" else L[L.lote == lote]
        fig.add_trace(go.Scattermap(lat=Lv.lat, lon=Lv.lon, mode="text", text=Lv.lote, showlegend=False, hoverinfo="skip",
                                    textfont=dict(size=13, color="#FFFFFF", weight=700)))
    capas = [dict(sourcetype="image", source=capa_png(capa, h, lote), below="traces",
                  coordinates=[[lon_o, lat_n], [lon_e, lat_n], [lon_e, lat_s], [lon_o, lat_s]])]
    if satelite:
        capas.insert(0, dict(sourcetype="raster", source=[ESRI], sourceattribution="Esri World Imagery", below="traces"))
    if lote == "Todos":
        centro, zoom = dict(lat=(lat_s + lat_n) / 2, lon=(lon_o + lon_e) / 2), 14.25
    else:
        f = L[L.lote == lote].iloc[0]
        centro, zoom = dict(lat=f.lat, lon=f.lon), 15.6
    fig.update_layout(map=dict(style="white-bg" if satelite else "carto-positron", center=centro, zoom=zoom, layers=capas),
                      margin=dict(l=0, r=0, t=0, b=0))
    return fig


__all__ = ["encabezado", "figura_mapa", "fecha_horizonte", "HORIZONTES"]
