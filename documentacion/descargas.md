# Procedencia y descarga de los datos

**Documentación organizada para entrega: 12/09/2026.** Esta reorganización mantiene los cinco
CSV y sus huellas. La evidencia HTTP/NTFS descrita abajo corresponde a la
revisión del **09/09/2026**, conservada en el registro JSON. No se descargaron
ni sustituyeron precios para reorganizar el proyecto. El 11/09/2026 se consultó
nuevamente la documentación EOD de Tiingo: el ajuste incorpora dividendos y
splits, por lo que no se agregan dividendos sobre `adjClose`.
[Fuente oficial](https://www.tiingo.com/documentation/end-of-day).

Las URLs de Cboe son las registradas en la verificación anterior; su consulta
documental no equivale a revalidar cada valor del archivo. El origen local
atribuido a SPY se volvió a buscar el 11/09/2026 sin encontrar el CSV en esa
ruta. Por ello se mantiene pendiente la vinculación con la petición original.

## Qué se pudo reconstruir

Los cinco CSV ya estaban en `datos_originales/` cuando se implementó el
análisis. El análisis no incluye un descargador. En la revisión documentada del
09/09/2026 se consultaron las fuentes oficiales y los metadatos de procedencia
de Windows, sin reemplazar ni modificar los archivos utilizados. Esta limpieza
no realizó consultas nuevas a los proveedores ni descargó precios.

Los atributos `HostUrl` del flujo NTFS `Zone.Identifier` identifican los
cuatro CSV de Cboe. Para SPY identifican una copia desde un archivo local.
Esta evidencia está conservada, junto con las huellas SHA-256, en
[procedencia_verificada.json](procedencia_verificada.json).

La **fecha exacta de la descarga original no está registrada** para ninguno
de los cinco archivos. Las fechas de modificación del sistema de archivos
no se toman como comprobante de descarga. Tampoco se confunden la cobertura
de los datos, la fecha de copia y la fecha de verificación de esta guía.
El registro [fuentes.csv](fuentes.csv) deja vacía `fecha_descarga` cuando no
hay evidencia suficiente.

## VIX.csv

- **Fuente:** Cboe, serie VIX. La página de
  [históricos del VIX](https://www.cboe.com/tradable_products/vix/vix_historical_data)
  ofrece datos diarios desde 1990.
- **URL original registrada:**
  [VIX_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv).
  El archivo se encuentra guardado localmente con el nombre `VIX.csv`.
- **Obtención reproducible:** abrir el enlace directo y guardar el CSV
  completo como `VIX.csv`. La URL no lleva filtros de fecha. El recorte al
  período del estudio se realiza en la copia de trabajo del análisis.
- **Acceso:** descarga pública por HTTPS. En la verificación del 09/09/2026 el enlace
  respondió HTTP 200 sin cuenta, token ni autenticación enviada.
- **Cobertura del archivo conservado:** 02/01/1990–04/09/2026; 9.266 filas.
- **Campos:** `DATE,OPEN,HIGH,LOW,CLOSE`. La fecha usa `MM/DD/AAAA`;
  el análisis utiliza exclusivamente `CLOSE` como nivel del VIX.

## PUT.csv

- **Fuente:** Cboe, serie PUT.
- **URL original registrada:**
  [PUT_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/PUT_History.csv).
  El nombre local es `PUT.csv`.
- **Obtención reproducible:** descargar el CSV completo del enlace directo
  y guardarlo con el nombre local. No se solicitan fechas en la URL.
- **Acceso:** HTTPS público; HTTP 200 sin cuenta ni token en la verificación.
- **Cobertura del archivo conservado:** 04/03/1991–04/09/2026; 4.957 filas.
  Antes de 2007 sólo hay siete observaciones aisladas: el primer y último
  registro no implican cobertura continua de todo ese intervalo.
- **Campos:** `DATE,PUT`, fecha `MM/DD/AAAA`. Se utiliza el nivel `PUT`.

## CNDR.csv

- **Fuente:** Cboe, serie CNDR.
- **URL original registrada:**
  [CNDR_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/CNDR_History.csv).
  El nombre local es `CNDR.csv`.
- **Obtención reproducible:** descargar el histórico completo desde ese
  enlace y guardarlo como `CNDR.csv`, sin filtros de fecha en la petición.
- **Acceso:** HTTPS público; HTTP 200 sin cuenta ni token en la verificación.
- **Cobertura del archivo conservado:** 20/06/1986–04/09/2026; 10.125 filas.
- **Campos:** `DATE,CNDR`, fecha `MM/DD/AAAA`. Se utiliza el nivel `CNDR`.

## PPUT.csv

- **Fuente:** Cboe, serie PPUT.
- **URL original registrada:**
  [PPUT_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/PPUT_History.csv).
  El nombre local es `PPUT.csv`.
- **Obtención reproducible:** descargar el histórico completo del enlace
  y guardarlo como `PPUT.csv`. La URL no tiene parámetros de fecha.
- **Acceso:** HTTPS público; HTTP 200 sin cuenta ni token en la verificación.
- **Cobertura del archivo conservado:** 30/06/1986–04/09/2026; 10.119 filas.
- **Campos:** `DATE,PPUT`, fecha `MM/DD/AAAA`. Se utiliza el nivel `PPUT`.

Los cuatro enlaces de Cboe se comprobaron leyendo únicamente el encabezado
de una respuesta HTTP. Sus encabezados coinciden con los de los archivos
locales. Esto documenta el acceso y formato en aquella revisión; no demuestra que el
histórico publicado posteriormente sea idéntico en todas sus filas a la copia guardada.

## SPY_Tiingo.csv

**Fuente indicada para la serie:** Tiingo End-of-Day, símbolo `SPY`.
El benchmark es un ETF y se utiliza su cierre ajustado `adjClose`.
La [documentación oficial de Tiingo EOD](https://www.tiingo.com/documentation/end-of-day)
describe ese campo y el endpoint de precios históricos.

**Origen local comprobado:** el atributo `HostUrl` apunta al archivo
`Time-Series-Momentum-with-VolatilityTargeting---MFin-2026-/descargas/SPY_Tiingo.csv`
dentro de Documentos. Acredita una copia desde otro proyecto, no una descarga
directa de Tiingo hacia esta carpeta. No se encontró allí ese CSV de origen
en la revisión del 11/09/2026. Posteriormente se recuperaron el pedido y
operaciones de descarga, con los límites que se detallan a continuación.
El manifiesto disponible de otro snapshot comienza en 2008 y no permite
atribuirle la descarga de este CSV, que comienza en 2007.

**Cobertura del archivo conservado:** 03/01/2007–31/12/2025; 4.780 filas.
Sus columnas, en orden, son `date,adjClose,close,divCash,splitFactor`, con
fechas `AAAA-MM-DD`. El programa sólo usa `date` y `adjClose`.

## Evidencia recuperada sobre SPY

El material de trabajo previo registró la confirmación del usuario de que SPY se obtuvo mediante la API de Tiingo con ayuda de un prompt. También recuperó el pedido y parte del script en un registro de conversación. Se traslada aquí esa evidencia documental; en esta limpieza no se volvió a consultar la conversación ni se ejecutó una descarga.

**Pedido recuperado del usuario, conservado literalmente:**

```text
descarga:



| ParámetroSelección                |                                   |
| --------------------------------- | --------------------------------- |
| Ticker                            | `SPY`                             |
| Frecuencia                        | Diaria                            |
| Desde                             | `2007-01-01`                      |
| Hasta                             | `2025-12-31`                      |
| Campos necesarios                 | `date`, `adjClose`                |
| Campos adicionales para controles | `close`, `divCash`, `splitFactor` |
| Archivo                           | `SPY_Tiingo.csv`                  |
```

El registro del mensaje tiene fecha **2026-09-09T14:41:13.931Z**. Es la fecha del pedido recuperado, no una fecha atribuida automáticamente al CSV actual. La evidencia proviene de la conversación identificada como `01a0868f-8cf5-78d1-b5ab-5c44c10bcbcd`, mensaje registrado en la línea 84; las llamadas de script relacionadas están en las líneas 104, 120 y 125. No se transfiere el registro completo, otras estrategias ni credenciales.

**Procedimiento recuperado del script ad hoc:** se ejecutó Python desde herramientas de terminal de Codex. El script importaba `TiingoClient` del módulo `momentum_volatility.data.tiingo_client`, cargaba la credencial mediante una función del cliente y solicitaba `client.get_eod_prices('SPY', start, end)`, con `start = date(2007,1,1)` y `end = date(2025,12,31)`. Se recuperaron estas operaciones:

1. Interpretar `response.raw_content` como JSON con `parse_float=Decimal`.
2. Seleccionar `date`, `adjClose`, `close`, `divCash` y `splitFactor` en ese orden.
3. Tomar la fecha publicada con `item['date'][:10]` y escribirla mediante `date.isoformat()`, sin conversión a una fecha distinta por huso horario.
4. Comprobar fechas dentro del intervalo y valores de control finitos; exigir precios ajustado/sin ajustar y factor de split positivos, y dividendos no negativos.
5. Validar las sesiones mediante `exchange_calendars`, calendario XNYS ampliado desde 2006-12-01 hasta 2026-01-31, y consultar el intervalo de 2007–2025.
6. Exportar mediante `csv.DictWriter`, con encabezado, coma y líneas terminadas en salto de línea, codificado en UTF-8.
7. Guardar el CSV como `SPY_Tiingo.csv`. El script también contemplaba respuesta original `SPY_Tiingo_raw.json` y manifiesto `SPY_Tiingo_manifest.json`, con SHA-256.

Esto permite describir la herramienta y transformaciones recuperadas, pero no convierte ese script en parte de la ejecución vigente. El módulo cliente y esos auxiliares no están disponibles en la versión actual de este proyecto. La carpeta de origen local documentada tampoco se encontró. No se recuperó una huella que vincule inequívocamente esa ejecución con el CSV actual; por tanto, **la fecha original de descarga de esta copia y su vinculación con el manifiesto siguen pendientes de confirmar**. No se inventa el contenido de la implementación interna del cliente.

## Procedimiento para volver a obtener una exportación equivalente

(documentado como reproducción, no como historial de una llamada observada):

1. Acceder a una cuenta de Tiingo y obtener un token con acceso al servicio
   End-of-Day. La API requiere token; la disponibilidad y los límites dependen
   del acceso de la cuenta. Para copiar el CSV ya existente sólo se necesita
   acceso al archivo local. La documentación de
   [conexión a Tiingo](https://www.tiingo.com/documentation/general/connecting)
   explica la autenticación.
2. Solicitar los precios diarios de SPY con estos parámetros:

   ```http
   GET https://api.tiingo.com/tiingo/daily/SPY/prices?startDate=2007-01-01&endDate=2025-12-31&resampleFreq=daily&format=json
   Authorization: Token <TOKEN_PERSONAL>
   ```

   El token se envía en el encabezado, no se incorpora a la URL ni a los
   archivos del proyecto. No se usó ningún token durante esta revisión.
3. Conservar la respuesta original por separado. Para reproducir la estructura
   del CSV utilizado, seleccionar `date,adjClose,close,divCash,splitFactor`
   en ese orden y expresar la fecha publicada como `AAAA-MM-DD`, sin trasladarla
   a otra fecha por conversión a la zona horaria local.
4. Exportar como `SPY_Tiingo.csv`, con comas y punto decimal, frecuencia diaria,
   sin agregar meses, rellenar faltantes ni volver a aplicar dividendos o splits.
   La selección coincide con las operaciones recuperadas del script. El endpoint
   completo se documenta para reproducción; sus parámetros HTTP internos no
   se verificaron sin el módulo cliente.

El `startDate` anterior es el inicio requerido del estudio; el primer registro
local efectivo es el 03/01/2007. Una descarga nueva puede reflejar revisiones
del proveedor y no garantiza el mismo archivo byte por byte. Se debe conservar
la copia usada en el estudio y contrastar su huella y sus controles.

## Período utilizado y conservación de evidencia

Para las cinco series, el análisis utiliza datos de **enero de 2007 a diciembre
de 2025**. Enero aporta la base; los rendimientos van de **febrero de 2007 a
diciembre de 2025**. VIX se usa con el cierre del mes anterior, con umbrales
30 y 25. No se utiliza información de 2026 en los cálculos.

El recorte temporal y las exclusiones de calendario quedan en
`resultados/controles/incidencias.csv`. Los campos, conteos y huellas de los
archivos efectivamente analizados están en
`resultados/controles/fuentes_verificadas.csv`.

Las transformaciones vigentes, las diez carteras, las fórmulas y el comando
de ejecución están en [README.md](../README.md) y [metodologia.md](metodologia.md). `datos_mensuales.csv` concentra
niveles, fechas de cierre, retornos y VIX previo. Los controles diarios y
exclusiones se consolidan en cuatro archivos; no se imputa ningún faltante.

Para repetir una descarga, guardar una copia nueva en otra carpeta y registrar
fuente, petición, fecha y hora, campos, acceso utilizado y SHA-256. Mantener
los cinco archivos de `datos_originales/` sin cambios permite reproducir el
estudio con el mismo conjunto de datos.

## Pendientes de procedencia

- Fechas originales de descarga de los cinco CSV; herramienta, autor y navegación originales de los cuatro archivos Cboe. Las fechas del sistema de archivos no prueban esas acciones.
- Vinculación inequívoca por SHA-256 entre el CSV SPY conservado y la descarga recuperada, su respuesta y manifiesto. El pedido tiene fecha propia, distinta de la descarga de esta copia.
- Plan, permisos y límites concretos de la cuenta Tiingo original, sólo si se necesita describir ese acceso histórico. No son necesarios para ejecutar con los CSV incluidos.
