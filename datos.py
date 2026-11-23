"""Datos y cálculos del tablero: pixeles del semáforo, lotes, plan de riego, mapas y clima."""

import base64
import datetime as dt
import io
import json
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

DATA = Path(__file__).parent / "data"

# La zona es un recorte de 200 × 200 pixeles de 10 m dentro de la rejilla de 500 × 500 del modelo A.
REJILLA_N, FILA0, COL0, LADO = 500, 150, 149, 200
HORIZONTES = (0, 7, 15, 30)
MIN_LOTE_PX = 50  # 0,5 ha
DIAS_A_ROJO_FIJO = 4.34  # mm de déficit que marcan "regar ya"


@st.cache_resource
def _firma_guardada() -> dict:
    return {}


def vigilar_datos() -> None:
    """Vacía la caché cuando la actualización diaria cambia algún archivo de data/."""
    firma = tuple((str(p), p.stat().st_mtime_ns) for p in sorted(DATA.rglob("*")) if p.is_file())
    guardada = _firma_guardada()
    if guardada.get("firma") not in (None, firma):
        st.cache_data.clear()
    guardada["firma"] = firma


@st.cache_data
def actualizacion() -> dict | None:
    ruta = DATA / "actualizacion.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


@st.cache_data
def resumen() -> dict:
    return json.loads((DATA / "semaforo/resumen.json").read_text(encoding="utf-8"))


def hoy() -> dt.date:
    return dt.date.fromisoformat(resumen()["hoy"])


@st.cache_data
def predio() -> pd.Series:
    return pd.read_parquet(DATA / "predio/predios_catalogo.parquet").iloc[0]


@st.cache_data
def curva_normal() -> pd.DataFrame:
    return pd.read_parquet(DATA / "cultivo/curva_normal_10anios.parquet")


def _etiquetar_lotes(px: pd.DataFrame) -> np.ndarray:
    """Lotes = áreas continuas de arroz con la misma fecha de siembra (±3 días), de al menos 0,5 ha.
    Los fragmentos pegados a un lote se le suman; los aislados quedan sin lote (0)."""
    das = np.full((LADO, LADO), np.nan)
    c = px[px.clase_h0 >= 0]
    das[c.fila, c.col] = c.das_hoy
    cult = ~np.isnan(das)
    vec = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    comp = np.zeros((LADO, LADO), int)
    k = 0
    for i, j in zip(*np.nonzero(cult)):
        if comp[i, j]:
            continue
        k += 1
        comp[i, j] = k
        q = deque([(i, j)])
        while q:
            a, b = q.popleft()
            for da, db in vec:
                x, y = a + da, b + db
                if 0 <= x < LADO and 0 <= y < LADO and cult[x, y] and not comp[x, y] and abs(das[x, y] - das[a, b]) <= 3:
                    comp[x, y] = k
                    q.append((x, y))
    tam = np.bincount(comp.ravel())
    grandes = [g for g in range(1, k + 1) if tam[g] >= MIN_LOTE_PX]
    lote = np.where(np.isin(comp, grandes), comp, 0)
    q = deque(zip(*np.nonzero(lote)))
    while q:
        a, b = q.popleft()
        for da, db in vec:
            x, y = a + da, b + db
            if 0 <= x < LADO and 0 <= y < LADO and cult[x, y] and not lote[x, y]:
                lote[x, y] = lote[a, b]
                q.append((x, y))
    centros = {g: np.argwhere(lote == g).mean(axis=0) for g in grandes}
    orden = sorted(grandes, key=lambda g: (round(centros[g][0] / 40), centros[g][1]))
    nombres = {g: f"L-{n:02d}" for n, g in enumerate(orden, 1)}
    salida = np.full((LADO, LADO), "", dtype=object)
    for g, nom in nombres.items():
        salida[lote == g] = nom
    salida[cult & (lote == 0)] = "Disperso"
    return salida


@st.cache_data
def pixeles() -> pd.DataFrame:
    px = pd.read_csv(DATA / "semaforo/pixeles.csv.gz")
    px["fila"] = px.pixel // REJILLA_N - FILA0
    px["col"] = px.pixel % REJILLA_N - COL0
    (lat_s, lon_o), (lat_n, lon_e) = resumen()["limites_latlon"]
    px["lat"] = lat_n - (px.fila + 0.5) / LADO * (lat_n - lat_s)
    px["lon"] = lon_o + (px.col + 0.5) / LADO * (lon_e - lon_o)
    for h in HORIZONTES:
        px[f"estado_h{h}"] = np.where(px[f"marca_h{h}"], 3, px[f"clase_h{h}"])
        px[f"agua_m3_h{h}"] = np.where(px[f"clase_h{h}"] >= 0, px[f"deficit_mm_h{h}"].clip(lower=0).fillna(0) * 0.1, 0.0)
    px["lote"] = _etiquetar_lotes(px)[px.fila, px.col]
    cn = curva_normal().set_index("das_b")
    banda = (px.das_hoy // 10 * 10).clip(0, 150)
    px["ndvi_normal"] = banda.map(cn.ndvi0_mean)
    px["vigor_z"] = (px.ndvi_h0 - px.ndvi_normal) / banda.map(cn.ndvi0_std)
    return px


def etapa(das: float) -> str:
    if das < 45:
        return "Vegetativa"
    if das < 82:
        return "Reproductiva"
    if das < 125:
        return "Maduración"
    return "Cosecha / socas"


@st.cache_data
def lotes() -> pd.DataFrame:
    px = pixeles()
    c = px[(px.clase_h0 >= 0) & (px.lote != "Disperso")]
    h0 = hoy()
    filas = []
    for nombre, g in c.groupby("lote"):
        das = float(g.das_hoy.mode().iloc[0])
        llega = g.dias_hasta_baja[g.dias_hasta_baja >= 0]
        dias_rojo = int(llega.median()) if len(llega) else 31
        rojo = float((g.clase_h0 == 2).mean())
        if rojo >= 0.2:
            accion, prioridad, limite = "Regar hoy", 1, h0
        elif dias_rojo <= 2:
            accion, prioridad, limite = "Regar en 1–2 días", 2, h0 + dt.timedelta(days=max(dias_rojo - 1, 0))
        elif dias_rojo <= 30:
            accion, prioridad, limite = "Programar riego", 3, h0 + dt.timedelta(days=dias_rojo - 1)
        else:
            accion, prioridad, limite = "Sin riego por ahora", 4, None
        z = float(g.vigor_z.mean())
        filas.append({
            "lote": nombre, "area_ha": len(g) / 100, "das": das, "etapa": etapa(das),
            "siembra": h0 - dt.timedelta(days=das), "accion": accion, "prioridad": prioridad, "fecha_limite": limite,
            "dias_a_rojo": dias_rojo, "pct_rojo": rojo, "pct_ambar": float((g.clase_h0 == 1).mean()), "pct_verde": float((g.clase_h0 == 0).mean()),
            "humedad_pct": float(g.humedad_pct_h0.mean()), "lamina_mm": float(g.deficit_mm_h0.clip(lower=0).mean()),
            "agua_hoy_m3": float(g.agua_m3_h0.sum()), "agua_7d_m3": float(g.agua_m3_h7.sum()),
            "ndvi": float(g.ndvi_h0.mean()), "ndvi_normal": float(g.ndvi_normal.mean()), "vigor_z": z,
            "vigor": "Bajo" if z < -1 else ("Alto" if z > 1 else "Normal"),
            "ndvi_30d": float(g.ndvi_h30.mean()), "ndmi": float(g.ndmi_h0.mean()), "alertas_px": int(g.marca_h0.sum()),
            "lat": float(g.lat.mean()), "lon": float(g.lon.mean()),
        })
    return pd.DataFrame(filas).sort_values(["prioridad", "fecha_limite", "pct_rojo"], ascending=[True, True, False]).reset_index(drop=True)


@st.cache_data
def pronostico() -> pd.DataFrame:
    g = pd.read_parquet(DATA / "clima/geos_s2s_corregido_latest.parquet")
    g["fecha"] = pd.to_datetime(g.fecha_objetivo).dt.date
    d = g.groupby("fecha").agg(lluvia=("lluvia_corr_mm", "mean"), lluvia_min=("lluvia_corr_mm", "min"),
                               lluvia_max=("lluvia_corr_mm", "max"), eto=("eto_corr_mm", "mean"),
                               tmax=("tx_corr_c", "mean"), tmin=("tn_corr_c", "mean")).reset_index()
    d["emision"] = g.emision.iloc[0]
    return d[d.fecha >= hoy()].reset_index(drop=True)


@st.cache_data
def pronostico_miembros() -> pd.DataFrame:
    g = pd.read_parquet(DATA / "clima/geos_s2s_corregido_latest.parquet")
    g["fecha"] = pd.to_datetime(g.fecha_objetivo).dt.date
    return g[g.fecha >= hoy()]


@st.cache_data
def clima_observado() -> pd.DataFrame:
    c = pd.read_parquet(DATA / "clima/clima_diario_1981_2026.parquet")
    c["fecha"] = pd.to_datetime(c.fecha)
    return c


# ----------------------------------------------------------------------------- mapas

CAPAS = {
    "Estado de riego": None,
    "Humedad del suelo (%)": ("humedad_pct", [(25.5, "#D6453D"), (27.1, "#F0A830"), (30, "#8BC48A"), (33, "#1F6F43")]),
    "Agua que falta (L/m²)": ("deficit_mm", [(0, "#F3F7F2"), (2, "#9CC3E0"), (4.34, "#2F6FA3"), (6.7, "#14385A")]),
    "Vigor del cultivo (NDVI)": ("ndvi", [(0.2, "#C9772B"), (0.5, "#F2D98A"), (0.7, "#8BC48A"), (0.9, "#1F6F43")]),
    "Agua en la planta (NDMI)": ("ndmi", [(-0.1, "#C9772B"), (0.15, "#F2D98A"), (0.3, "#9CC3E0"), (0.5, "#2F6FA3")]),
    "Días hasta regar ya": ("dias_hasta_baja", [(0, "#D6453D"), (3, "#F0A830"), (7, "#F2D98A"), (30, "#8BC48A")]),
}
COLOR_ESTADO = {0: (46, 158, 91), 1: (240, 168, 48), 2: (214, 69, 61), 3: (124, 92, 196)}


def _hex(c: str) -> np.ndarray:
    return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], float)


def colorear(valores: np.ndarray, paradas: list[tuple[float, str]]) -> np.ndarray:
    xs = np.array([p for p, _ in paradas])
    cs = np.array([_hex(c) for _, c in paradas])
    v = np.clip(valores, xs[0], xs[-1])
    return np.stack([np.interp(v, xs, cs[:, k]) for k in range(3)], axis=-1)


@st.cache_data
def capa_png(capa: str, h: int, lote: str) -> str:
    px = pixeles()
    sel = px[px[f"clase_h{h}"] >= 0]
    if lote != "Todos":
        sel = sel[sel.lote == lote]
    img = np.zeros((LADO, LADO, 4), np.uint8)
    if CAPAS[capa] is None:
        rgb = np.array([COLOR_ESTADO[e] for e in sel[f"estado_h{h}"]], float)
    else:
        col, paradas = CAPAS[capa]
        nombre = col if col == "dias_hasta_baja" else f"{col}_h{h}"
        v = sel[nombre].to_numpy(float)
        if col == "dias_hasta_baja":
            v = np.where(v < 0, 30, v)
        rgb = colorear(v, paradas)
    img[sel.fila, sel.col, :3] = rgb.astype(np.uint8)
    img[sel.fila, sel.col, 3] = 230
    buf = io.BytesIO()
    Image.fromarray(img).resize((LADO * 4, LADO * 4), Image.NEAREST).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def geojson_prescripcion(df: pd.DataFrame, h: int) -> str:
    (lat_s, lon_o), (lat_n, lon_e) = resumen()["limites_latlon"]
    dlat, dlon = (lat_n - lat_s) / LADO, (lon_e - lon_o) / LADO
    feats = []
    for r in df.itertuples():
        n, o = lat_n - r.fila * dlat, lon_o + r.col * dlon
        anillo = [[round(o, 7), round(n, 7)], [round(o + dlon, 7), round(n, 7)], [round(o + dlon, 7), round(n - dlat, 7)],
                  [round(o, 7), round(n - dlat, 7)], [round(o, 7), round(n, 7)]]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [anillo]},
                      "properties": {"pixel": int(r.pixel), "lote": r.lote, "estado": int(getattr(r, f"estado_h{h}")),
                                     "lamina_mm": round(float(max(getattr(r, f"deficit_mm_h{h}"), 0)), 2),
                                     "agua_m3": round(float(getattr(r, f"agua_m3_h{h}")), 3)}})
    return json.dumps({"type": "FeatureCollection", "features": feats})
