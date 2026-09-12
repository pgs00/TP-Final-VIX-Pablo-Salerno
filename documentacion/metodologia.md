# Metodología y resultados de referencia

Detalle del análisis implementado en `analisis.py`. Para instalar, ejecutar y localizar las salidas, consultar el [README](../README.md).

## Series y significado

Las descripciones siguientes expresan el significado utilizado en el código y documentación del proyecto; no constituyen una reconstrucción de las metodologías contractuales de los índices.

| Serie | Qué representa en el trabajo | Campo y unidad | Función |
| --- | --- | --- | --- |
| VIX | Índice de volatilidad utilizado como señal de régimen. | `CLOSE`, puntos del VIX. | Clasifica el mes siguiente; no se invierte capital en VIX. |
| PUT | Índice de estrategia de venta de puts respaldada por letras del Tesoro. | `PUT`, puntos de índice. | Inversión permanente o activo de una condicional. |
| CNDR | Índice de estrategia con opciones de tipo iron condor. | `CNDR`, puntos de índice. | Inversión permanente o activo de una condicional. |
| PPUT | Índice que combina exposición al S&P 500 con puts de protección. | `PPUT`, puntos de índice. | Inversión permanente o activo de una condicional. |
| SPY | ETF utilizado como benchmark; no se presenta como el índice oficial S&P 500 Total Return. | `adjClose`, precio ajustado del ETF en USD por participación. | Inversión permanente y activo de las condicionales cuando la señal no activa su índice. |

Se utilizan niveles publicados; no se reconstruyen operaciones de opciones ni se añade apalancamiento. Los puntos de los distintos índices no se comparan directamente como montos de dinero: se calculan sus retornos y se aplican a un capital inicial común.

## Datos y transformaciones

| Archivo | Campo fecha y formato | Valor utilizado |
| --- | --- | --- |
| VIX.csv | DATE, MM/DD/AAAA | CLOSE |
| PUT.csv | DATE, MM/DD/AAAA | PUT |
| CNDR.csv | DATE, MM/DD/AAAA | CNDR |
| PPUT.csv | DATE, MM/DD/AAAA | PPUT |
| SPY_Tiingo.csv | date, AAAA-MM-DD | adjClose |

Se verifica encabezado, cantidad de columnas, coma, punto decimal y lectura
UTF-8 compatible con BOM. Fechas inválidas o duplicadas detienen el proceso.
Valores ausentes, no numéricos, infinitos, cero o negativos se registran y
quedan ausentes. Las filas se ordenan sólo en la copia de trabajo.

El período diario es **enero de 2007–diciembre de 2025**, con calendario común
NYSE de `pandas_market_calendars`. El calendario es una regla de validación,
no una fuente de precios. Se documentan cobertura completa y exclusiones
fuera de período/calendario, sin declarar erróneo el dato de origen.

Se exige un valor válido en la **última sesión NYSE del mes**, sin sustituirlo
por un dato anterior. Un faltante intramensual no invalida el retorno si
ambos cierres necesarios existen. No se interpola ni se arrastran datos.
Los niveles consecutivos iguales se conservan: no prueban imputación de origen.
Se verifican las huellas SHA-256 de los originales antes y después del cálculo.

La [guía de fuentes y descarga](descargas.md) explica URLs,
procedimientos conocidos y límites de procedencia. Las fechas exactas de
descarga siguen pendientes. Para SPY se conservan la evidencia de copia local y el pedido/procedimiento
recuperado; sigue pendiente vincular por huella esa ejecución con este CSV.

## Carteras y fórmulas

**Principal:** siempre SPY, siempre PUT, siempre CNDR, siempre PPUT y tres
carteras que usan, respectivamente, PUT, CNDR o PPUT si el **VIX del cierre
anterior es >= 30**; usan SPY el resto. Cada condicional mantiene su índice.
**Sensibilidad:** sólo las tres condicionales con umbral 25. Las permanentes
se presentan una sola vez y no necesitan señal VIX.

Por ejemplo, febrero de 2007 usa el VIX del 31/01/2007. La asignación teórica
es del 100% a un activo cada mes; no se usa el VIX al final del mes del retorno.
No se modelan precios de ejecución ni la posibilidad operativa de rebalancear
exactamente en el cierre en que se observa la señal.

```text
r[t] = nivel[t] / nivel[t-1] - 1
C[enero 2007] = USD 10.000
C[t] = C[t-1] × (1 + retorno asignado[t])
Rendimiento acumulado = C[final] / 10.000 - 1
Rendimiento anual compuesto = (C[final] / 10.000)^(12 / cantidad de meses) - 1
Caída[t] = C[t] / máximo(C[enero 2007], ..., C[t]) - 1
Máxima caída acumulada, medida con cierres mensuales = mínimo(Caída[t])
```

Son **228 cierres y 227 rendimientos**, de febrero de 2007 a diciembre de
2025. Enero aporta la base. No hay aportes ni retiros. SPY es un ETF y usa
`adjClose`, sin volver a sumar dividendos. Se usan los niveles publicados
de los índices, sin reconstruir contratos ni agregar apalancamiento.

La máxima caída incluye el capital inicial, es negativa o cero y **no es
el peor retorno de un mes**, ni mide caídas intramensuales. El CAGR usa 227
meses de rendimiento, no 228 cierres. Si falta señal o retorno necesario,
la trayectoria queda incompleta desde ese mes y no se reanuda; sus cuatro
métricas finales quedan vacías. Se informa el primer mes y motivo. Un dato
faltante de un activo no seleccionado no afecta a la cartera.

## Episodios

Los grupos son enero 2008–diciembre 2009, enero–diciembre 2020, enero–diciembre
2022 y todos los meses restantes: **24, 12, 12 y 179 meses**, incluidos aquellos
en SPY. Para cada grupo y cada condicional:

```text
Factor relativo = producto(1 + retorno cartera) / producto(1 + retorno SPY)
Ventaja relativa = factor relativo - 1
Producto de los cuatro factores = capital final cartera / capital final SPY
```

**Los porcentajes no se suman:** +10% y -10% producen 1,10 × 0,90 = 0,99,
ventaja -1%. «Meses restantes» es una agrupación de atribución, no un período
continuo: no se calcula una caída concatenándolos. Todos los episodios siguen
en las métricas generales. Un retorno aplicado o SPY faltante hace incompleto
el grupo, sin omitir el mes; tras interrumpirse una trayectoria tampoco se
aplican sus retornos posteriores. Un grupo vacío tendría factor 1 y estado
`sin_meses`.

## Lectura de los descriptivos

Se informa media, mediana, desvío muestral (`ddof=1`), proporción
de meses negativos y peor retorno mensual, sin anualizar.
`diferencia_media_vs_spy_pp` es la media de diferencias en **meses pareados**,
en puntos porcentuales, con `cantidad_pares_vs_spy`. Grupos vacíos: n=0 y
métricas vacías; con n<2 no hay desvío. Alto incluye la igualdad; bajo significa
VIX previo inferior al umbral. Son descriptivos, no carteras con VIX bajo.

Las asignaciones se calculan internamente en `simular_carteras`; no se exportan en un CSV separado. La regla, la señal previa y los retornos se pueden seguir en las tablas mensuales y en `comparacion_carteras.csv`.

## Resultados con los originales conservados

Se verifican 4.780 sesiones NYSE. CNDR y PPUT tienen seis faltantes diarios,
el 03/12/2018, 05/07/2019 y 16/10/2020, sin afectar cierres. Se excluyen 27
observaciones VIX fuera del calendario y 15.326 observaciones fuera del período;
se conservan 56 repeticiones. No hay duplicados ni valores inválidos utilizados.
Los cinco cierres coinciden en 228 meses; las diez carteras están completas.
VIX 30: 22 meses altos y 205 bajos; VIX 25: 45 altos y 182 bajos.

| Cartera | Capital final USD | Acumulado % | Anual compuesto % | Máxima caída acumulada, medida con cierres mensuales % |
| --- | ---: | ---: | ---: | ---: |
| Siempre SPY | 67.513,02 | 575,13 | 10,62 | -50,80 |
| Siempre PUT | 35.452,00 | 254,52 | 6,92 | -32,66 |
| Siempre CNDR | 10.990,60 | 9,91 | 0,50 | -18,96 |
| Siempre PPUT | 43.177,26 | 331,77 | 8,04 | -38,92 |
| PUT condicional 30 | 61.313,61 | 513,14 | 10,06 | -45,39 |
| CNDR condicional 30 | 55.433,86 | 454,34 | 9,48 | -30,94 |
| PPUT condicional 30 | 70.971,19 | 609,71 | 10,92 | -36,70 |
| PUT condicional 25 — sensibilidad | 61.104,53 | 511,05 | 10,04 | -43,14 |
| CNDR condicional 25 — sensibilidad | 46.483,85 | 364,84 | 8,46 | -28,46 |
| PPUT condicional 25 — sensibilidad | 64.505,18 | 545,05 | 10,36 | -38,50 |

Las tres condicionales 30 reducen la máxima caída frente a SPY. PUT y CNDR
terminan con menos capital; PPUT lo supera en aproximadamente 5,12% relativo.
Frente a sus índices permanentes, las tres condicionales 30 producen mayor
capital, pero PUT y CNDR tienen caídas máximas más profundas; PPUT también
reduce esa caída. La protección depende del comparador y de la medida elegida.

| Ventaja relativa del grupo | 2008–2009 % | 2020 % | 2022 % | Meses restantes % |
| --- | ---: | ---: | ---: | ---: |
| PUT condicional 30 | 3,78 | -11,12 | -5,04 | 3,69 |
| CNDR condicional 30 | 17,84 | -19,54 | -11,76 | -1,86 |
| PPUT condicional 30 | 14,27 | 3,32 | -4,60 | -6,67 |

2008–2009 aporta ventaja relativa a las tres; 2022 aporta desventaja a todas.
En 2020 sólo PPUT tiene aporte positivo. PPUT compensa 2022 y el resto con
2008–2009 y 2020; no implica protección en cada crisis. Con umbral 25 ninguna
condicional supera el capital final de SPY: el resultado favorable de PPUT 30
no se mantiene en esa sensibilidad. No se infiere superioridad futura.

## Orientación para el informe

Una estructura de **8 páginas**: pregunta y alcance (1); datos, fuentes y VIX
(1); reglas y fórmulas (1); comparación principal y capitales (2); caídas y
episodios (1); sensibilidad y descriptivos (1); conclusiones, límites y
referencias (1). Se puede ajustar a 6–10 páginas manteniendo la misma pregunta
y los tres gráficos; la bitácora y controles sirven como respaldo técnico.

