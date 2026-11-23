# SIRA · Riego de arroz por pixel

Tablero operativo de SIRA para agricultores y agrónomos del Alto Magdalena. Dice qué lotes regar, cuándo y con cuánta agua, a partir del semáforo de humedad del suelo por pixel de 10 m, el pronóstico del clima de la NASA y el estado del cultivo visto por satélite.

Cubre 400 ha alrededor del C.I. Nataima (El Espinal, Tolima) y se actualiza solo cada día (ver [Actualización diaria](#actualización-diaria)).

## Páginas

| Página | Para qué sirve |
|---|---|
| Hoy | Hectáreas a regar hoy y antes de la fecha límite, mapa del semáforo, prioridades por lote, clima de los próximos 7 días |
| Mapa | Mapa satelital por pixel con capas de estado de riego, humedad, agua que falta, vigor (NDVI), agua en la planta (NDMI) y días hasta «regar ya»; filtro por lote y fecha; descarga del mapa de prescripción en CSV y GeoJSON |
| Plan de riego | Calendario de 14 días por lote, fecha límite de riego, lámina (mm) y volumen (m³) hoy y si se espera 7 días; descarga del plan |
| Clima | Pronóstico diario de lluvia y evapotranspiración a 28 días con sus escenarios, balance de agua acumulado, resumen semanal y lluvia observada |
| Cultivo | Etapa y edad de cada lote, vigor frente a la curva normal del arroz, puntos para revisar en campo con enlace al mapa |
| Datos y modelo | Fecha de cada fuente, confiabilidad del sistema, parámetros del suelo y supuestos de la corrida |

Los lotes son áreas continuas de arroz con la misma fecha de siembra, de 0,5 ha o más, detectadas en los pixeles del semáforo.

## Ejecutarlo

Necesitas Python 3.11 o superior.

```powershell
cd sira-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

En macOS o Linux, la activación es `source .venv/bin/activate`. Se abre en `http://localhost:8501`. La imagen satelital y la tipografía se cargan de internet.

## Actualización diaria

Cada día a las 5:30 a. m. (hora de Colombia), GitHub Actions corre `actualizar.py` ([`.github/workflows/actualizar.yml`](.github/workflows/actualizar.yml)) y trae:

| Dato | De dónde sale | Cuándo cambia |
|---|---|---|
| Semáforo por pixel | La última corrida publicada en [GomSal/SIRA](https://github.com/GomSal/SIRA/tree/modelo-humedad/reports/semaforo_c), rama `modelo-humedad`, carpeta `reports/semaforo_c` | Cuando el equipo publica una corrida nueva |
| Pronóstico GEOS-S2S | El inicio que usó esa corrida, corregido como en `semaforo_c.py`; el promedio de los escenarios debe dar la lluvia y la ETo acumuladas que guardó la corrida | Con cada corrida |
| Lluvia y ETo observadas | NASA POWER, CHIRPS y Open-Meteo, con las reglas de la tabla `clima_dia` del pipeline de clima | Cada día |

Si algo cambió, el workflow hace commit de `data/` y Streamlit Community Cloud vuelve a publicar la app en un par de minutos. Si una fuente falla, su archivo queda como estaba y el workflow termina en rojo; GitHub avisa por correo.

El semáforo no se recalcula aquí: necesita el cubo de imágenes y los modelos del equipo, que no están en GitHub. Para que el tablero muestre una corrida nueva, basta con publicarla en `reports/semaforo_c` de la rama `modelo-humedad`.

Para correrlo a mano: en GitHub, **Actions** → **Actualizar datos** → **Run workflow**. En el computador:

```powershell
python actualizar.py --seco   # revisa todo sin escribir
python actualizar.py
```

## Publicarlo en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio de GitHub.
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub y elige **Create app**.
3. Selecciona el repositorio, la rama y `app.py`; en **Advanced settings** elige Python 3.12.
4. **Deploy** y comparte el enlace.

## Estructura

```
app.py        navegación y barra lateral
actualizar.py actualización diaria de data/ (la corre .github/workflows/actualizar.yml)
comun.py      encabezado del predio y mapa satelital
datos.py      lectura de datos, lotes, plan de riego y capas del mapa
estilo.py     colores, tipografía y componentes
paginas/      una página por pantalla
data/         semáforo por pixel, pronóstico GEOS-S2S, clima diario desde 1981, curva normal del NDVI, suelo del predio y fecha de la última actualización
```

Los datos vienen del repositorio [GomSal/SIRA](https://github.com/GomSal/SIRA) (ramas `modelo-humedad` y `Big-Data_Arch`) y de la tabla `clima_dia` del pipeline de clima.
