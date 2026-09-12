# Trabajo final de Ingeniería Financiera — UCEMA

El proyecto compara el rendimiento y las caídas de PUT, CNDR y PPUT cuando
se activan con **VIX del cierre mensual anterior ≥ 30**, frente a mantener
esos índices permanentemente o invertir siempre en SPY. El umbral 25 se usa
como sensibilidad, sin optimización. El estudio abarca enero de 2007 a
diciembre de 2025; enero aporta el capital inicial de USD 10.000.

`analisis.py` es el único punto de entrada. Lee cinco CSV locales y genera
una simulación teórica con índices. Los resultados finales están únicamente
en `resultados/`.

## Estructura

```text
README.md                 Guía de ejecución y lectura de resultados
analisis.py               Análisis, exportación y controles
requirements.txt          Versiones de las dependencias
.gitignore                Exclusiones del entorno y archivos locales/privados
.gitattributes            Conservación de bytes y huellas al usar Git
datos_originales/         Los cinco CSV conservados sin modificaciones
documentacion/            Fuentes, descarga, metodología, bitácora y verificación
tests/                    Pruebas de datos, carteras, episodios y flujo completo
resultados/
  tablas/                 Cinco tablas de la corrida final
  graficos/               Tres gráficos de esa misma corrida
  controles/              Cuatro archivos de trazabilidad y validación
```

El entorno local `.venv/` se conserva para trabajar y se excluye de la entrega.
`.gitattributes` evita conversiones automáticas de finales de línea que
cambiarían las huellas SHA-256 al agregar o extraer archivos con Git.

## Datos y fuentes

Los archivos deben estar en `datos_originales/`, con estos nombres y campos:

| Archivo | Fuente | Fecha | Campo utilizado |
| --- | --- | --- | --- |
| VIX.csv | Cboe, VIX | `DATE`, MM/DD/AAAA | `CLOSE` |
| PUT.csv | Cboe, PUT | `DATE`, MM/DD/AAAA | `PUT` |
| CNDR.csv | Cboe, CNDR | `DATE`, MM/DD/AAAA | `CNDR` |
| PPUT.csv | Cboe, PPUT | `DATE`, MM/DD/AAAA | `PPUT` |
| SPY_Tiingo.csv | Tiingo, ETF SPY | `date`, AAAA-MM-DD | `adjClose` |

La [guía de descarga](documentacion/descargas.md) conserva los enlaces,
formatos, procedimiento recuperado para SPY y límites de procedencia.
[fuentes.csv](documentacion/fuentes.csv) y
[procedencia_verificada.json](documentacion/procedencia_verificada.json)
registran la evidencia y las huellas de los originales.

**La descarga no está automatizada en este proyecto.** Con los CSV incluidos,
el análisis no necesita conexión a Cboe/Tiingo ni credenciales. Una nueva
descarga puede incorporar revisiones del proveedor: debe guardarse aparte
para no sustituir la muestra utilizada.

## Instalación y ejecución

Desde PowerShell, situado en la carpeta del proyecto. El entorno verificado
usa **Python 3.14.3**; el requisito declarado del proyecto es Python 3.12+.
Las dependencias están fijadas en `requirements.txt`.

Para una instalación nueva:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si se utiliza el entorno ya preparado, ejecutar directamente:

```powershell
.\.venv\Scripts\python.exe analisis.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

No hace falta activar el entorno. Las rutas se resuelven desde la ubicación
de `analisis.py`. El script no recibe argumentos y cada ejecución actualiza
los mismos archivos de `resultados/`. Para preservar una corrida durante una
verificación, copiar el proyecto a otra carpeta y ejecutar allí el script.
Los tests usan carpetas temporales para sus salidas.

## Resultados finales

La corrida incluida es la del **11/09/2026 a las 20:05:53 UTC**. Fue contrastada
con una ejecución aislada de la versión limpia; el detalle está en la
[verificación de entrega](documentacion/limpieza.md).

| Tabla en `resultados/tablas/` | Lectura |
| --- | --- |
| [comparacion_carteras.csv](resultados/tablas/comparacion_carteras.csv) | Resultado principal: diez carteras, capital final, rendimiento acumulado, CAGR, máxima caída y estado. Siete principales y tres de sensibilidad. |
| [capitales_mensuales.csv](resultados/tablas/capitales_mensuales.csv) | Las diez trayectorias en USD; 228 filas incluida la base. |
| [datos_mensuales.csv](resultados/tablas/datos_mensuales.csv) | Niveles, cierres, retornos, VIX previo y regímenes 30/25; 228 filas. |
| [aporte_episodios.csv](resultados/tablas/aporte_episodios.csv) | Atribución multiplicativa por cuatro grupos para seis condicionales; 24 filas. |
| [descriptivos_regimen.csv](resultados/tablas/descriptivos_regimen.csv) | Estadísticas mensuales y tamaños de muestra por régimen; 16 filas. |

Los gráficos de `resultados/graficos/` muestran el VIX y los umbrales
(`01_vix_umbrales.png`), los capitales principales (`02_capitales_vix_30.png`)
y las caídas desde máximos (`03_caidas_vix_30.png`).

Los CSV usan UTF-8 con BOM, coma, punto decimal y 15 cifras significativas.
Los retornos mensuales son decimales; las métricas y ventajas están en %.
Una celda vacía representa un valor ausente. En Excel, importar mediante
**Datos → Desde texto/CSV**.

## Cómo reconocer una ejecución exitosa

El proceso debe terminar con código 0 y el mensaje de verificación. Consultar
siempre estos archivos de `resultados/controles/`:

| Control | Qué acredita |
| --- | --- |
| [ejecucion.json](resultados/controles/ejecucion.json) | `estado: correcto`, `error: null`, parámetros, versiones, verificaciones y SHA-256 del código, requisitos y once salidas. |
| [fuentes_verificadas.csv](resultados/controles/fuentes_verificadas.csv) | Cobertura, formato y SHA-256 inicial/final de cada original; `original_sin_cambios: True`. |
| [cierres_mensuales.csv](resultados/controles/cierres_mensuales.csv) | 1.140 registros: cierre esperado/usado y disponibilidad mensual por serie. |
| [incidencias.csv](resultados/controles/incidencias.csv) | Exclusiones, faltantes, repeticiones y, si las hubiera, interrupciones. Se conservan aunque no aparezcan en el informe. |

Con los originales incluidos se esperan **4.780 sesiones NYSE, 228 cierres
por serie, 227 retornos por inversión y 10/10 carteras completas**. Hay seis
faltantes diarios intramensuales sin imputar. Los regímenes tienen 22/205
meses altos/bajos con umbral 30 y 45/182 con umbral 25. Las 22 pruebas deben
terminar en `OK`.

Un error devuelve código 1 y puede dejar salidas parciales o anteriores;
la presencia de gráficos no demuestra éxito. Revisar también los estados
individuales de las carteras: `estado: correcto` indica que terminó el flujo,
y una cartera incompleta se informa por separado.

## Supuestos y limitaciones

Se exige el cierre de la última sesión NYSE del mes; no se interpolan ni
arrastran datos. Las condicionales asignan el 100% a su índice fijo si se
cumple la señal previa y a SPY el resto. No se modelan costos adicionales de
rotación, impuestos, aportes, retiros ni precios operativos de rebalanceo.
SPY es un ETF con `adjClose`, no el índice oficial S&P 500 Total Return;
no se suman dividendos nuevamente.

Las caídas se miden con cierres mensuales e incluyen el capital inicial.
El enfoque se refinó tras observar resultados iniciales y no tiene validación
fuera de muestra. La ventaja de capital de PPUT con umbral 30 no se mantiene
con 25. La fecha original de descarga de los cinco CSV y la vinculación por
huella de SPY con la petición recuperada siguen pendientes.

Las [reglas, fórmulas y resultados de referencia](documentacion/metodologia.md)
desarrollan estos puntos. La [bitácora](documentacion/bitacora.md) documenta
decisiones y uso de IA; la [reorganización de 2026](documentacion/reorganizacion.md)
explica la evolución que dio lugar al análisis vigente.
