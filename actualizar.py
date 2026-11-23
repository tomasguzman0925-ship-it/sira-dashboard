"""Actualiza los datos del tablero con lo último publicado. GitHub Actions lo corre cada día a las 5:30 a. m.

1. Semáforo: la última corrida publicada en GomSal/SIRA (rama modelo-humedad, reports/semaforo_c).
2. Pronóstico: GEOS-S2S del inicio que usó esa corrida, corregido igual que en scripts/operacion/semaforo_c.py.
   Control: el promedio de los escenarios da la lluvia y la ETo acumuladas que guardó la corrida.
3. Clima observado: NASA POWER, CHIRPS y Open-Meteo con las reglas de la tabla clima_dia del pipeline de clima.
   Control: las columnas calculadas de los días que no cambian quedan idénticas.

Cada paso que falla deja su archivo como estaba y el script termina con error. Solo escribe lo que cambió.

    python actualizar.py [--seco]
"""

import argparse
import datetime as dt
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"
SIRA = "https://raw.githubusercontent.com/GomSal/SIRA/modelo-humedad"
COLOMBIA = dt.timezone(dt.timedelta(hours=-5))
REJILLA_N, FILA0, COL0, LADO = 500, 150, 149, 200
HORIZONTES = [0, 7, 15, 30]

SELLO, ANIOS, HORIZONTE = pd.Timestamp("2025-11-18"), 10, 30

LAT, LON, ALTITUD_M = 4.1913, -74.9609, 323.0
FACTOR_ETO_OPEN_METEO = 0.7824145828526875
DIFERENCIA_MAX_TEMP_C = 3.0
UMBRAL_LLUVIA_MM = 2.0
COLUMNAS_CLIMA = ["fecha", "lluvia_mm", "fuente_lluvia", "lluvia_5d_mm", "dias_sin_lluvia", "temp_max_c", "temp_min_c",
                  "humedad_rel_pct", "rad_solar_mj_m2", "eto_mm", "fuente_eto", "atwd_5d_mm", "gdd_arroz_c"]

ARCHIVOS = {
    "resumen": DATA / "semaforo/resumen.json",
    "pixeles": DATA / "semaforo/pixeles.csv.gz",
    "geos": DATA / "clima/geos_s2s_corregido_latest.parquet",
    "clima": DATA / "clima/clima_diario_1981_2026.parquet",
    "estado": DATA / "actualizacion.json",
}

T0 = time.time()


def log(mensaje: str) -> None:
    print(f"[{time.time() - T0:5.0f} s] {mensaje}", flush=True)


def bajar(url: str, params: dict | None = None, intentos: int = 4, espera_max: int = 300) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(url, timeout=espera_max) as r:
                return r.read()
        except Exception as error:  # noqa: BLE001
            if intento == intentos:
                raise RuntimeError(f"falló tras {intentos} intentos: {url} ({error})") from error
            time.sleep(5 * intento)
    raise AssertionError


def bajar_json(url: str, params: dict | None = None, **kw) -> dict | list:
    return json.loads(bajar(url, params, **kw))


# ----------------------------------------------------------------------------- 1. semáforo


def semaforo(actual: dict) -> tuple[dict, dict[Path, bytes]]:
    crudo = bajar(f"{SIRA}/reports/semaforo_c/resumen.json")
    nuevo = json.loads(crudo)
    if nuevo["hoy"] < actual["hoy"]:
        log(f"semáforo: la corrida publicada ({nuevo['hoy']}) es anterior a la del tablero ({actual['hoy']}); se deja")
        return actual, {}
    assert [h["h"] for h in nuevo["horizontes"]] == HORIZONTES, "horizontes distintos de 0, 7, 15 y 30"
    for clave in ("geos_inicio", "zona_ha", "limites_latlon", "modelo_b", "dias_hasta_baja_sin_riego_pct"):
        assert clave in nuevo, f"resumen.json sin {clave}"

    gz = bajar(f"{SIRA}/reports/semaforo_c/pixeles.csv.gz")
    px = pd.read_csv(io.BytesIO(gz), compression="gzip")
    faltan = set(pd.read_csv(ARCHIVOS["pixeles"], nrows=0).columns) - set(px.columns)
    assert not faltan, f"pixeles.csv.gz sin las columnas {sorted(faltan)}"
    fila, col = px.pixel // REJILLA_N - FILA0, px.pixel % REJILLA_N - COL0
    assert fila.between(0, LADO - 1).all() and col.between(0, LADO - 1).all(), "pixeles fuera de la zona del tablero"
    assert px.pixel.is_unique, "pixeles repetidos"

    cambios = {}
    if crudo != ARCHIVOS["resumen"].read_bytes():
        cambios[ARCHIVOS["resumen"]] = crudo
    if gz != ARCHIVOS["pixeles"].read_bytes():
        cambios[ARCHIVOS["pixeles"]] = gz
    estado = "nueva" if nuevo["hoy"] > actual["hoy"] else ("revisada" if cambios else "sin cambios")
    log(f"semáforo: corrida del {nuevo['hoy']} ({estado}) · {len(px):,} pixeles · "
        f"hoy {nuevo['horizontes'][0]['suficiente']['pct']} % suficiente, {nuevo['horizontes'][0]['media']['pct']} % "
        f"regar pronto, {nuevo['horizontes'][0]['baja']['pct']} % regar ya")
    return nuevo, cambios


# ----------------------------------------------------------------------------- 2. pronóstico GEOS-S2S


def pronostico(R: dict, clima: pd.DataFrame) -> pd.DataFrame:
    hoy = pd.Timestamp(R["hoy"])
    c = clima.set_index("fecha")
    per = c.loc[SELLO - pd.DateOffset(years=ANIOS):SELLO - pd.Timedelta(days=1)]
    doy = per.index.day_of_year
    clim_eto, clim_ll = per.eto_mm.groupby(doy).mean(), per.lluvia_mm.groupby(doy).mean()
    clim_t = ((per.temp_max_c + per.temp_min_c) / 2).groupby(doy).mean()

    corr = pd.read_csv(io.BytesIO(bajar(f"{SIRA}/reports/modelo_a/entrenamiento_final/paso8_geos_correccion.csv")))
    fac = {(r.variable, int(r.mes), int(r.plazo)): r.factor for r in corr.itertuples()}
    g = pd.read_csv(io.BytesIO(bajar(f"{SIRA}/data/processed/modelo_a/geos/geos_nrt.csv")), parse_dates=["fecha"])
    g["inicio"] = pd.to_datetime(g.inicio.astype(str))
    ini = pd.Timestamp(R["geos_inicio"])
    g = g[g.inicio == ini]
    assert len(g), f"el GEOS-S2S publicado no tiene el inicio {R['geos_inicio']} que usó la corrida"
    gp = g.pivot_table(index=["miembro", "fecha"], columns="variable", values="valor").reset_index()
    for v in ("pr_sfc", "t2mmax", "t2mmin"):
        if v not in gp:
            gp[v] = np.nan
    plz = np.select([(gp.fecha - ini).dt.days <= 10, (gp.fecha - ini).dt.days <= 20], [0, 1], 2)
    mes = gp.fecha.dt.month
    f_pr = np.array([fac.get(("pr", m, p), 1.0) for m, p in zip(mes, plz)])
    f_t = np.array([fac.get(("t", m, p), 0.0) for m, p in zip(mes, plz)])
    gp["pr_raw"] = gp.pr_sfc * 86400
    gp["pr"] = gp.pr_raw * f_pr
    gp["tx"] = gp.t2mmax - 273.15 + f_t
    gp["tn"] = gp.t2mmin - 273.15 + f_t
    d = gp.fecha.dt.day_of_year
    gp["eto"] = d.map(clim_eto) * ((gp.tx + gp.tn) / 2 + 17.8) / (d.map(clim_t) + 17.8)

    fechas = pd.date_range(ini + pd.Timedelta(days=1), hoy + pd.Timedelta(days=HORIZONTE))
    filas = []
    for mb in sorted(gp.miembro.unique()):
        q = gp[gp.miembro == mb].set_index("fecha").reindex(fechas)
        sin = q.pr.isna() | q.eto.isna()
        filas.append(pd.DataFrame({
            "celda_clima_id": "CELDA_4.0_-75.0", "emision": str(ini.date()), "miembro": int(mb),
            "fecha_objetivo": fechas.strftime("%Y-%m-%d"), "plazo": (fechas - ini).days,
            "pr_raw_mm": q.pr_raw.to_numpy(),
            "lluvia_corr_mm": q.pr.fillna(pd.Series(fechas.day_of_year.map(clim_ll), index=fechas)).to_numpy(),
            "tx_corr_c": q.tx.to_numpy(), "tn_corr_c": q.tn.to_numpy(),
            "eto_corr_mm": q.eto.fillna(pd.Series(fechas.day_of_year.map(clim_eto), index=fechas)).to_numpy(),
            "eto_es_relleno_clim": sin.to_numpy()}))
    out = pd.concat(filas, ignore_index=True)
    assert out.miembro.nunique() == R["miembros_geos"], "número de escenarios distinto al de la corrida"

    futuro = out[pd.to_datetime(out.fecha_objetivo) > hoy]
    media = futuro.groupby("fecha_objetivo")[["lluvia_corr_mm", "eto_corr_mm"]].mean().cumsum()
    if "diario" in R:
        ref = pd.DataFrame(R["diario"]).set_index("fecha").loc[media.index]
        tol = 0.06
    else:
        ref = pd.DataFrame(R["horizontes"]).set_index("fecha").loc[lambda x: x.h > 0]
        tol = 0.5
    dif = max((media.loc[ref.index, "lluvia_corr_mm"] - ref.lluvia_mm_hasta_h).abs().max(),
              (media.loc[ref.index, "eto_corr_mm"] - ref.eto_mm_hasta_h).abs().max())
    assert dif <= tol, f"el pronóstico no reproduce la lluvia y la ETo de la corrida (diferencia {dif:.2f} mm)"
    log(f"pronóstico: GEOS-S2S del {ini.date()} · {out.miembro.nunique()} escenarios · hasta {fechas[-1].date()} · "
        f"control contra la corrida: diferencia máxima {dif:.3f} mm")
    return out


# ----------------------------------------------------------------------------- 3. clima observado


def open_meteo() -> pd.DataFrame:
    d = bajar_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": LAT, "longitude": LON, "past_days": 92, "forecast_days": 1, "timezone": "America/Bogota",
        "daily": "precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max"})["daily"]
    return pd.DataFrame(d).assign(fecha=lambda x: pd.to_datetime(x.time)).set_index("fecha").drop(columns="time")


def nasa_power(inicio: dt.date, fin: dt.date) -> pd.DataFrame:
    d = bajar_json("https://power.larc.nasa.gov/api/temporal/daily/point", {
        "parameters": "T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN", "community": "AG", "latitude": LAT,
        "longitude": LON, "start": f"{inicio:%Y%m%d}", "end": f"{fin:%Y%m%d}", "format": "JSON"})
    relleno = d["header"]["fill_value"]
    p = pd.DataFrame(d["properties"]["parameter"]).replace(relleno, np.nan)
    p.index = pd.to_datetime(p.index, format="%Y%m%d")
    return p


def chirps(inicio: dt.date, fin: dt.date, espera_max_s: int = 600) -> pd.Series:
    base = "https://climateserv.servirglobal.net/chirps"
    m = 0.025
    anillo = [[LON - m, LAT - m], [LON + m, LAT - m], [LON + m, LAT + m], [LON - m, LAT + m], [LON - m, LAT - m]]
    trabajo = bajar_json(f"{base}/submitDataRequest/", {
        "datatype": 0, "begintime": f"{inicio:%m/%d/%Y}", "endtime": f"{fin:%m/%d/%Y}", "intervaltype": 0,
        "operationtype": 5, "geometry": json.dumps({"type": "Polygon", "coordinates": [anillo]})})[0]
    limite = time.time() + espera_max_s
    while True:
        progreso = bajar_json(f"{base}/getDataRequestProgress/", {"id": trabajo})[0]
        if progreso >= 100:
            break
        if progreso < 0 or time.time() > limite:
            raise RuntimeError(f"CHIRPS no terminó el trabajo {trabajo} (progreso {progreso})")
        time.sleep(10)
    datos = bajar_json(f"{base}/getDataFromRequest/", {"id": trabajo})["data"]
    s = pd.Series({pd.Timestamp(x["year"], x["month"], x["day"]): x["value"]["avg"] for x in datos}, dtype=float)
    return s[s >= 0].sort_index()


def eto_fao56(tmax, tmin, rh, u2, rs, fecha) -> pd.Series:
    tmed = (tmax + tmin) / 2
    e0 = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))  # noqa: E731
    es = (e0(tmax) + e0(tmin)) / 2
    ea = es * rh / 100
    delta = 4098 * e0(tmed) / (tmed + 237.3)**2
    gamma = 0.000665 * 101.3 * ((293 - 0.0065 * ALTITUD_M) / 293)**5.26
    j = fecha.day_of_year.to_numpy()
    phi = math.radians(LAT)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    decl = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(-math.tan(phi) * np.tan(decl))
    ra = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * np.sin(decl) + math.cos(phi) * np.cos(decl) * np.sin(ws))
    rso = (0.75 + 2e-5 * ALTITUD_M) * ra
    kt = np.minimum(rs / rso, 1.0)
    rnl = 4.903e-9 * ((tmax + 273.16)**4 + (tmin + 273.16)**4) / 2 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * kt - 0.35)
    rn = 0.77 * rs - rnl
    eto = (0.408 * delta * rn + gamma * 900 / (tmed + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    return eto.clip(lower=0)


def derivadas(c: pd.DataFrame) -> pd.DataFrame:
    c = c.sort_index().copy()
    c["lluvia_5d_mm"] = c.lluvia_mm.rolling(5, min_periods=1).sum()
    c["atwd_5d_mm"] = c.eto_mm.rolling(5, min_periods=1).mean() - c.lluvia_mm.rolling(5, min_periods=1).mean()
    grupo = (c.lluvia_mm >= UMBRAL_LLUVIA_MM).cumsum()
    c["dias_sin_lluvia"] = c.groupby(grupo).cumcount().astype("int32")
    c["gdd_arroz_c"] = ((c.temp_max_c + c.temp_min_c) / 2 - 10).clip(lower=0).fillna(0.0)
    return c


def clima(actual: pd.DataFrame) -> pd.DataFrame:
    hoy = dt.datetime.now(COLOMBIA).date()
    ayer = hoy - dt.timedelta(days=1)
    c = actual.set_index("fecha")
    om = open_meteo()
    om = om[om.index.date < hoy]
    power = nasa_power(hoy - dt.timedelta(days=30), ayer)
    try:
        ch = chirps(hoy - dt.timedelta(days=90), ayer)
    except Exception as error:  # noqa: BLE001
        log(f"clima: CHIRPS no respondió ({error}); se deja la lluvia que había")
        ch = pd.Series(dtype=float)

    idx = om.index.union(power.dropna(how="all").index).union(ch.index)
    base = c.reindex(idx)
    p = power.reindex(idx)
    o = om.reindex(idx)
    ch = ch.reindex(idx)

    era_chirps = base.fuente_lluvia.eq("CHIRPS")
    lluvia = ch.where(ch.notna(), base.lluvia_mm.where(era_chirps, o.precipitation_sum))
    lluvia = lluvia.where(lluvia.notna(), base.lluvia_mm)
    fuente_ll = pd.Series(np.where(ch.notna() | era_chirps, "CHIRPS",
                                   np.where(o.precipitation_sum.notna(), "Open-Meteo", base.fuente_lluvia)), index=idx)

    con_power = p.T2M_MAX.notna()
    tmax = p.T2M_MAX.where(con_power, base.temp_max_c)
    tmin = p.T2M_MIN.where(con_power, base.temp_min_c)
    rh = p.RH2M.where(con_power, base.humedad_rel_pct)
    rad = p.ALLSKY_SFC_SW_DWN.where(p.ALLSKY_SFC_SW_DWN.notna(), base.rad_solar_mj_m2)
    eto_p = eto_fao56(p.T2M_MAX, p.T2M_MIN, p.RH2M, p.WS2M, p.ALLSKY_SFC_SW_DWN, idx)
    sospechoso = (p.T2M_MAX - o.temperature_2m_max).abs() > DIFERENCIA_MAX_TEMP_C
    confiable = eto_p.notna() & ~sospechoso
    queda_power = eto_p.isna() & base.fuente_eto.eq("NASA POWER")
    eto_om = o.et0_fao_evapotranspiration * FACTOR_ETO_OPEN_METEO
    eto = eto_p.where(confiable, base.eto_mm.where(queda_power, eto_om.where(eto_om.notna(), base.eto_mm)))
    fuente_eto = pd.Series(np.where(confiable, "NASA POWER", np.where(queda_power, "NASA POWER", np.where(
        eto_om.notna(), "Open-Meteo ajustada", base.fuente_eto))), index=idx)

    nuevas = pd.DataFrame({"lluvia_mm": lluvia, "fuente_lluvia": fuente_ll, "temp_max_c": tmax, "temp_min_c": tmin,
                           "humedad_rel_pct": rh, "rad_solar_mj_m2": rad, "eto_mm": eto, "fuente_eto": fuente_eto})
    nuevas = nuevas[nuevas.lluvia_mm.notna() & nuevas.eto_mm.notna()]
    todo = pd.concat([c.drop(index=nuevas.index, errors="ignore"), nuevas]).sort_index()
    todo = derivadas(todo)

    previo = c.index[c.index < idx.min()]
    for col in ("lluvia_5d_mm", "atwd_5d_mm", "dias_sin_lluvia", "gdd_arroz_c"):
        assert np.allclose(c.loc[previo, col], todo.loc[previo, col], equal_nan=True), \
            f"las columnas calculadas no reproducen {col} de la tabla clima_dia"
    todo.loc[previo] = c.loc[previo, todo.columns]

    todo = todo.reset_index(names="fecha")[COLUMNAS_CLIMA]
    for col in COLUMNAS_CLIMA:
        todo[col] = todo[col].astype(actual[col].dtype)
    viejo = c.loc[c.index >= idx.min(), todo.columns[1:]]
    cambiados = todo.set_index("fecha").loc[viejo.index].round(6).compare(viejo.round(6)).index.nunique()
    log(f"clima: hasta {todo.fecha.max().date()} ({len(todo) - len(actual)} días nuevos, {cambiados} revisados) · "
        f"CHIRPS hasta {todo.fecha[todo.fuente_lluvia == 'CHIRPS'].max().date()} · "
        f"NASA POWER confiable hasta {todo.fecha[todo.fuente_eto == 'NASA POWER'].max().date()}")
    return todo


# ----------------------------------------------------------------------------- principal


def a_parquet(df: pd.DataFrame) -> bytes:
    b = io.BytesIO()
    df.to_parquet(b, index=False)
    return b.getvalue()


def igual(df: pd.DataFrame, ruta: Path) -> bool:
    if not ruta.exists():
        return False
    viejo = pd.read_parquet(ruta)
    return viejo.shape == df.shape and viejo.equals(df.astype(viejo.dtypes))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seco", action="store_true", help="revisa todo y no escribe nada")
    a = ap.parse_args()

    escribir: dict[Path, bytes] = {}
    errores = []
    R = json.loads(ARCHIVOS["resumen"].read_text(encoding="utf-8"))
    clima_actual = pd.read_parquet(ARCHIVOS["clima"])

    try:
        R, cambios = semaforo(R)
        escribir |= cambios
    except Exception as error:  # noqa: BLE001
        errores.append(f"semáforo: {error}")

    clima_nuevo = clima_actual
    try:
        clima_nuevo = clima(clima_actual)
        if not igual(clima_nuevo, ARCHIVOS["clima"]):
            escribir[ARCHIVOS["clima"]] = a_parquet(clima_nuevo)
    except Exception as error:  # noqa: BLE001
        errores.append(f"clima: {error}")

    try:
        g = pronostico(R, clima_nuevo)
        if not igual(g, ARCHIVOS["geos"]):
            escribir[ARCHIVOS["geos"]] = a_parquet(g)
    except Exception as error:  # noqa: BLE001
        errores.append(f"pronóstico: {error}")

    for e in errores:
        log(f"ERROR {e}")
    if escribir:
        g = pd.read_parquet(io.BytesIO(escribir[ARCHIVOS["geos"]])) if ARCHIVOS["geos"] in escribir \
            else pd.read_parquet(ARCHIVOS["geos"])
        estado = {
            "revisado": dt.datetime.now(COLOMBIA).isoformat(timespec="minutes"),
            "semaforo": R["hoy"], "geos_inicio": str(g.emision.iloc[0]),
            "clima_hasta": str(clima_nuevo.fecha.max().date()),
            "archivos": sorted(str(r.relative_to(DATA)).replace("\\", "/") for r in escribir), "errores": errores,
        }
        escribir[ARCHIVOS["estado"]] = (json.dumps(estado, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    log(("se escribirían: " if a.seco else "escritos: ") + (", ".join(
        str(r.relative_to(DATA)).replace("\\", "/") for r in escribir) or "nada"))
    if not a.seco:
        for ruta, contenido in escribir.items():
            ruta.write_bytes(contenido)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
