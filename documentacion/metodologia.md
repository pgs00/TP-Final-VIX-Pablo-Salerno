# Metodología y resultados de referencia

Este documento resume las reglas implementadas en `analisis.py`, las fórmulas utilizadas y los resultados de referencia. Para instalar, ejecutar y localizar las salidas, consultar el [README](../README.md).

## Series utilizadas

| Serie | Representación en el trabajo | Campo utilizado | Función |
| --- | --- | --- | --- |
| VIX | Índice de volatilidad utilizado como señal de régimen | `CLOSE` | Clasifica el mes siguiente |
| PUT | Índice de estrategia de venta de puts respaldada por letras del Tesoro | `PUT` | Inversión permanente o activo de una condicional |
| CNDR | Índice de estrategia iron condor | `CNDR` | Inversión permanente o activo de una condicional |
| PPUT | Índice que combina exposición al S&P 500 con puts de protección | `PPUT` | Inversión permanente o activo de una condicional |
| SPY | ETF utilizado como benchmark | `adjClose` | Inversión permanente y activo de las condicionales cuando no se activa su índice |

Se utilizan los niveles publicados de los índices y no se reconstruyen operaciones individuales con opciones. Los niveles de PUT, CNDR y PPUT se transforman en rendimientos antes de aplicarlos al capital inicial común.

## Datos y validación

Los cinco archivos se encuentran en `datos_originales/`:

| Archivo | Campo de fecha | Valor utilizado |
| --- | --- | --- |
| `VIX.csv` | `DATE`, MM/DD/AAAA | `CLOSE` |
| `PUT.csv` | `DATE`, MM/DD/AAAA | `PUT` |
| `CNDR.csv` | `DATE`, MM/DD/AAAA | `CNDR` |
| `PPUT.csv` | `DATE`, MM/DD/AAAA | `PPUT` |
| `SPY_Tiingo.csv` | `date`, AAAA-MM-DD | `adjClose` |

El análisis cubre de enero de 2007 a diciembre de 2025. Enero de 2007 se utiliza como base y los rendimientos van de febrero de 2007 a diciembre de 2025.

El programa verifica encabezados, formato de fechas, duplicados y valores numéricos positivos. Las observaciones se restringen al calendario NYSE mediante `pandas_market_calendars`.

Se exige un valor válido en la última sesión NYSE de cada mes. No se interpola, no se arrastran precios y no se sustituye un cierre faltante por un dato anterior. Los faltantes intramensuales se documentan, pero no invalidan un retorno si existen los dos cierres mensuales requeridos.

Los archivos originales no se modifican durante la ejecución. El flujo registra controles de cobertura e integridad en `resultados/controles/`.

La [guía de fuentes y descarga](descargas.md) documenta los proveedores, enlaces oficiales y el procedimiento para volver a obtener las series.

## Construcción de las carteras

### Escenario principal

Se comparan siete carteras:

- Siempre SPY.
- Siempre PUT.
- Siempre CNDR.
- Siempre PPUT.
- PUT condicional.
- CNDR condicional.
- PPUT condicional.

Las tres condicionales utilizan su índice asignado cuando el **VIX del cierre del mes anterior es mayor o igual a 30**. En los demás meses mantienen SPY.

Por ejemplo, el rendimiento de febrero de 2007 utiliza como señal el VIX del cierre de enero de 2007. El VIX observado al final del propio mes de rendimiento no interviene en la decisión.

### Sensibilidad

La misma regla se repite con un umbral de **25**. En este escenario se recalculan únicamente las tres carteras condicionales. Las cuatro inversiones permanentes conservan sus resultados.

Con umbral 30 se observan 22 meses de régimen alto y 205 de régimen bajo. Con umbral 25 se observan 45 meses altos y 182 bajos.

## Fórmulas

Para cada activo:

```text
r[t] = nivel[t] / nivel[t-1] - 1
```

El capital inicial es:

```text
C[enero 2007] = USD 10.000
```

Y cada mes se actualiza como:

```text
C[t] = C[t-1] × (1 + retorno asignado[t])
```

El rendimiento acumulado se calcula como:

```text
C[final] / C[inicial] - 1
```

El rendimiento anual compuesto utiliza los 227 meses de rendimiento:

```text
(C[final] / C[inicial])^(12 / 227) - 1
```

La caída desde máximos se define como:

```text
Caída[t] = C[t] / máximo(C[enero 2007], ..., C[t]) - 1
```

La máxima caída acumulada es el valor más negativo de esa serie. Se calcula con cierres mensuales e incluye el capital inicial.

## Regla ante faltantes

Si falta una señal VIX necesaria o un rendimiento del activo que corresponde utilizar, la trayectoria afectada queda incompleta desde ese mes y no se reanuda posteriormente. No se reemplazan faltantes por cero ni se saltan meses.

Un faltante de un activo que no corresponde utilizar ese mes no afecta a la cartera.

## Descriptivos por régimen

Para cada umbral y régimen se calculan:

- cantidad de observaciones;
- rendimiento medio;
- mediana;
- desvío estándar muestral (`ddof=1`);
- porcentaje de meses negativos;
- peor rendimiento mensual;
- diferencia media frente a SPY en meses pareados.

Estas métricas son descriptivas y no se anualizan.

## Aporte relativo de episodios

Los 227 meses de rendimiento se agrupan en:

- 2008 y 2009: 24 meses;
- 2020: 12 meses;
- 2022: 12 meses;
- meses restantes: 179 meses.

Para cada grupo y cartera condicional:

```text
Factor relativo = producto(1 + retorno cartera) / producto(1 + retorno SPY)
Ventaja relativa = factor relativo - 1
```

Los porcentajes de los grupos no son aditivos. Los factores relativos se multiplican para reconstruir la diferencia total frente a SPY.

La agrupación de “meses restantes” se utiliza únicamente para atribución y no constituye un período continuo para calcular caídas.

## Resultados de referencia

La muestra final contiene 228 cierres mensuales y 227 rendimientos. Las diez carteras quedan completas.

| Cartera | Capital final USD | Rendimiento anual compuesto | Máxima caída |
| --- | ---: | ---: | ---: |
| Siempre SPY | 67.513,02 | 10,62% | -50,80% |
| Siempre PUT | 35.452,00 | 6,92% | -32,66% |
| Siempre CNDR | 10.990,60 | 0,50% | -18,96% |
| Siempre PPUT | 43.177,26 | 8,04% | -38,92% |
| PUT condicional 30 | 61.313,61 | 10,06% | -45,39% |
| CNDR condicional 30 | 55.433,86 | 9,48% | -30,94% |
| PPUT condicional 30 | 70.971,19 | 10,92% | -36,70% |
| PUT condicional 25 | 61.104,53 | 10,04% | -43,14% |
| CNDR condicional 25 | 46.483,85 | 8,46% | -28,46% |
| PPUT condicional 25 | 64.505,18 | 10,36% | -38,50% |

Con umbral 30, las tres condicionales presentan una máxima caída menos profunda que SPY. PPUT condicional es la única que además termina con mayor capital final que SPY.

Con umbral 25, ninguna condicional supera el capital final de SPY, aunque las tres conservan una máxima caída menor que el benchmark. Por lo tanto, la ventaja de rentabilidad observada para PPUT con umbral 30 no es robusta al cambio de umbral.

## Episodios con umbral 30

| Condicional | 2008-2009 | 2020 | 2022 | Resto |
| --- | ---: | ---: | ---: | ---: |
| PUT | 3,78% | -11,12% | -5,04% | 3,69% |
| CNDR | 17,84% | -19,54% | -11,76% | -1,86% |
| PPUT | 14,27% | 3,32% | -4,60% | -6,67% |

Los resultados no son uniformes entre episodios. 2008-2009 favorece relativamente a las tres reglas, 2022 perjudica a las tres y en 2020 sólo PPUT presenta una ventaja positiva frente a SPY.

## Supuestos y limitaciones

La simulación utiliza índices teóricos y no reconstruye contratos negociables. No se modelan costos adicionales de rotación, impuestos ni precios efectivos de ejecución.

SPY se trata como ETF y utiliza `adjClose`, por lo que no se agregan dividendos nuevamente.

Las caídas se miden con cierres mensuales y pueden subestimar pérdidas intramensuales. La muestra contiene pocos meses de VIX alto y el enfoque fue refinado después de observar resultados iniciales. No se realizaron pruebas de significación ni una evaluación fuera de muestra.

Por estos motivos, los resultados se interpretan como una comparación histórica de rendimiento y caídas dentro de la muestra, no como evidencia de una estrategia óptima o de superioridad futura.
