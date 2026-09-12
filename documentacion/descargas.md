# Fuentes y descarga de los datos

Este documento resume las fuentes utilizadas por el proyecto y cómo volver a obtener una copia equivalente de cada serie.

Los cinco archivos exactos utilizados en el estudio están incluidos en `datos_originales/`. El análisis trabaja con esas copias locales y no requiere conexión a internet ni credenciales para ejecutarse.

El período utilizado por el análisis es **enero de 2007 a diciembre de 2025**. Enero de 2007 aporta la base y los rendimientos se calculan desde febrero de 2007.

## VIX

- **Proveedor:** Cboe.
- **Serie:** VIX.
- **Archivo local:** `datos_originales/VIX.csv`.
- **Fuente oficial:** histórico diario de VIX de Cboe.
- **URL directa:** `https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`
- **Campos del archivo:** `DATE, OPEN, HIGH, LOW, CLOSE`.
- **Campo utilizado:** `CLOSE`.
- **Formato de fecha:** `MM/DD/AAAA`.

Para obtener una nueva copia, descargar el CSV histórico de Cboe y guardarlo como `VIX.csv`. El análisis recorta internamente el período requerido.

## PUT

- **Proveedor:** Cboe.
- **Serie:** Cboe S&P 500 PutWrite Index.
- **Archivo local:** `datos_originales/PUT.csv`.
- **URL directa:** `https://cdn.cboe.com/api/global/us_indices/daily_prices/PUT_History.csv`
- **Campos del archivo:** `DATE, PUT`.
- **Campo utilizado:** `PUT`.
- **Formato de fecha:** `MM/DD/AAAA`.

Para obtener una nueva copia, descargar el histórico de Cboe y guardarlo como `PUT.csv`.

## CNDR

- **Proveedor:** Cboe.
- **Serie:** Cboe S&P 500 Iron Condor Index.
- **Archivo local:** `datos_originales/CNDR.csv`.
- **URL directa:** `https://cdn.cboe.com/api/global/us_indices/daily_prices/CNDR_History.csv`
- **Campos del archivo:** `DATE, CNDR`.
- **Campo utilizado:** `CNDR`.
- **Formato de fecha:** `MM/DD/AAAA`.

Para obtener una nueva copia, descargar el histórico de Cboe y guardarlo como `CNDR.csv`.

## PPUT

- **Proveedor:** Cboe.
- **Serie:** Cboe S&P 500 Put Protection Index.
- **Archivo local:** `datos_originales/PPUT.csv`.
- **URL directa:** `https://cdn.cboe.com/api/global/us_indices/daily_prices/PPUT_History.csv`
- **Campos del archivo:** `DATE, PPUT`.
- **Campo utilizado:** `PPUT`.
- **Formato de fecha:** `MM/DD/AAAA`.

Para obtener una nueva copia, descargar el histórico de Cboe y guardarlo como `PPUT.csv`.

## SPY

- **Proveedor:** Tiingo.
- **Activo:** SPDR S&P 500 ETF Trust (`SPY`).
- **Archivo local:** `datos_originales/SPY_Tiingo.csv`.
- **Servicio:** Tiingo End-of-Day.
- **Documentación oficial:** `https://www.tiingo.com/documentation/end-of-day`
- **Endpoint de referencia:** `https://api.tiingo.com/tiingo/daily/SPY/prices`
- **Campos conservados:** `date, adjClose, close, divCash, splitFactor`.
- **Campo utilizado por el análisis:** `adjClose`.
- **Formato de fecha:** `AAAA-MM-DD`.

Para volver a obtener una copia equivalente se necesita una cuenta de Tiingo y un token con acceso End-of-Day. La consulta debe solicitar SPY con frecuencia diaria entre `2007-01-01` y `2025-12-31`.

Un ejemplo de los parámetros de la petición es:

```text
Ticker: SPY
Frecuencia: diaria
Desde: 2007-01-01
Hasta: 2025-12-31
Campos: date, adjClose, close, divCash, splitFactor
Archivo: SPY_Tiingo.csv
```

El proyecto utiliza `adjClose`, que incorpora los ajustes correspondientes según la definición del proveedor, por lo que no se agregan dividendos o splits nuevamente.

## Formato esperado

Los archivos de Cboe utilizan coma como separador, punto decimal y fechas en formato estadounidense. El archivo de Tiingo utiliza coma, punto decimal y fechas ISO.

El programa verifica los encabezados esperados, fechas, duplicados y valores numéricos antes de construir la muestra mensual.

## Conservación de los datos utilizados

Las copias exactas utilizadas en el trabajo se mantienen en `datos_originales/` y no son modificadas por `analisis.py`.

Una nueva descarga desde un proveedor podría incorporar actualizaciones de sus históricos. Por ese motivo, para reproducir exactamente los resultados entregados debe utilizarse el conjunto de archivos incluido en el repositorio.

Para más detalle sobre el tratamiento de los datos, cierres mensuales, señal VIX y construcción de carteras, consultar [`metodologia.md`](metodologia.md).
