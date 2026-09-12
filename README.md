# Trabajo final de Ingeniería Financiera — UCEMA

Este proyecto compara el rendimiento y las caídas de estrategias con opciones representadas por los índices **PUT**, **CNDR** y **PPUT** cuando se activan con el **VIX del cierre mensual anterior ≥ 30**, frente a mantener esos índices permanentemente o invertir siempre en **SPY**. El umbral 25 se utiliza como análisis de sensibilidad, sin optimización.

El estudio abarca de enero de 2007 a diciembre de 2025. Enero de 2007 aporta el capital inicial de USD 10.000 y los rendimientos se calculan desde febrero de 2007 hasta diciembre de 2025.

`analisis.py` es el único punto de entrada. Lee cinco CSV locales, valida la muestra, construye las carteras y genera tablas, gráficos y controles de consistencia.

## Estructura del repositorio

```text
README.md                 Guía del proyecto y ejecución
analisis.py               Análisis, simulación, exportación y controles
requirements.txt          Dependencias del entorno
.gitignore                Exclusiones de archivos locales y privados
.gitattributes            Conservación de bytes al versionar archivos
datos_originales/         Cinco CSV utilizados en el estudio
documentacion/
  descargas.md            Fuentes y procedimiento para volver a obtener las series
  metodologia.md          Reglas, fórmulas y resultados de referencia
tests/                    Pruebas del análisis y del flujo completo
resultados/
  tablas/                 Tablas generadas por la corrida final
  graficos/               Gráficos generados por la corrida final
  controles/              Validaciones y trazabilidad de la ejecución
```

El entorno local `.venv/` no forma parte de la entrega.

## Datos y fuentes

Los archivos utilizados deben estar en `datos_originales/` con estos nombres y campos:

| Archivo | Fuente | Fecha | Campo utilizado |
| --- | --- | --- | --- |
| `VIX.csv` | Cboe, VIX | `DATE`, MM/DD/AAAA | `CLOSE` |
| `PUT.csv` | Cboe, PUT | `DATE`, MM/DD/AAAA | `PUT` |
| `CNDR.csv` | Cboe, CNDR | `DATE`, MM/DD/AAAA | `CNDR` |
| `PPUT.csv` | Cboe, PPUT | `DATE`, MM/DD/AAAA | `PPUT` |
| `SPY_Tiingo.csv` | Tiingo, ETF SPY | `date`, AAAA-MM-DD | `adjClose` |

Los cuatro históricos de Cboe son públicos. Una nueva descarga de SPY desde Tiingo requiere una cuenta y un token con acceso End-of-Day. Como los cinco CSV utilizados en el estudio están incluidos en `datos_originales/`, la ejecución del análisis no necesita conexión ni credenciales.

La guía de fuentes y descarga está en [`documentacion/descargas.md`](documentacion/descargas.md).

## Instalación

El proyecto requiere Python 3.12 o superior. Las versiones verificadas de las dependencias están fijadas en `requirements.txt`.

Desde PowerShell, ubicado en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

También puede utilizarse otro entorno de Python 3.12+ con las mismas dependencias.

## Ejecución

Con el entorno activado:

```powershell
python analisis.py
```

O sin activarlo:

```powershell
.\.venv\Scripts\python.exe analisis.py
```

Para ejecutar las pruebas:

```powershell
python -m unittest discover -s tests -v
```

El script no recibe argumentos y actualiza los archivos de `resultados/`.

## Resultados generados

`resultados/tablas/` contiene:

- `comparacion_carteras.csv`: capital final, rendimiento acumulado, rendimiento anual compuesto, máxima caída y estado de las diez carteras.
- `capitales_mensuales.csv`: trayectorias mensuales de capital.
- `datos_mensuales.csv`: niveles, cierres, retornos, VIX previo y regímenes 30/25.
- `aporte_episodios.csv`: atribución relativa frente a SPY por grupos de episodios.
- `descriptivos_regimen.csv`: estadísticas mensuales por régimen de VIX.

`resultados/graficos/` contiene:

- `01_vix_umbrales.png`
- `02_capitales_vix_30.png`
- `03_caidas_vix_30.png`

`resultados/controles/` contiene:

- `ejecucion.json`: estado de la corrida, parámetros y verificaciones.
- `fuentes_verificadas.csv`: cobertura y controles de los cinco originales.
- `cierres_mensuales.csv`: cierre esperado y utilizado por mes y serie.
- `incidencias.csv`: exclusiones, faltantes y otras incidencias registradas.

Con los archivos incluidos se esperan 4.780 sesiones NYSE, 228 cierres por serie, 227 rendimientos por inversión y 10 de 10 carteras completas. Hay seis faltantes diarios intramensuales que no afectan los cierres mensuales requeridos.

## Metodología resumida

Se comparan cuatro inversiones permanentes, SPY, PUT, CNDR y PPUT, y tres carteras condicionales. Cada cartera condicional utiliza su índice asignado cuando el VIX del cierre del mes anterior es mayor o igual al umbral y mantiene SPY en los demás meses.

La regla principal utiliza VIX ≥ 30. La sensibilidad repite las tres condicionales con VIX ≥ 25. La decisión se aplica al rendimiento del mes siguiente, por lo que febrero de 2007 utiliza la señal del cierre de enero de 2007.

Los rendimientos mensuales se calculan entre cierres consecutivos de la última sesión NYSE de cada mes. No se interpolan ni arrastran datos. El capital se reinvierte completamente, sin aportes ni retiros.

Las métricas principales son capital final, rendimiento anual compuesto y máxima caída acumulada medida con cierres mensuales.

El detalle de reglas y fórmulas está en [`documentacion/metodologia.md`](documentacion/metodologia.md).

## Supuestos y limitaciones

La simulación utiliza niveles publicados de índices de estrategias y no reconstruye operaciones individuales con opciones. No se modelan costos adicionales de rotación, impuestos ni precios efectivos de ejecución.

SPY se trata como ETF y utiliza `adjClose`, por lo que no se suman dividendos nuevamente. La máxima caída se mide con cierres mensuales y puede no reflejar mínimos intramensuales.

El enfoque se refinó después de observar resultados iniciales, no incluye una evaluación fuera de muestra y contiene pocos meses de VIX alto. La ventaja de capital observada para PPUT condicional con umbral 30 no se mantiene al reducir el umbral a 25, por lo que no se interpreta como evidencia de superioridad estable o futura.

## Fuentes

Las fuentes principales son Cboe para VIX, PUT, CNDR y PPUT, y Tiingo para SPY. Los enlaces oficiales y el procedimiento para volver a obtener las series están documentados en [`documentacion/descargas.md`](documentacion/descargas.md).
