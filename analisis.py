"""Trabajo final de Ingeniería Financiera (UCEMA).

Compara PUT, CNDR y PPUT con SPY (ETF, cierre ajustado de Tiingo),
clasificando los rendimientos con el cierre del VIX del mes anterior.
Lee exclusivamente los cinco CSV locales y nunca modifica los originales.
"""

import csv
import hashlib
import io
import json
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Guarda PNG sin requerir una ventana o sesión gráfica.
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal


# 1. PARÁMETROS DEL ESTUDIO
FECHA_INICIO_DATOS = "2007-01-01"
FECHA_FIN_DATOS = "2025-12-31"
FRECUENCIA_DATOS = "diaria"
FECHA_INICIO_ANALISIS = "2007-02-01"
FECHA_FIN_ANALISIS = "2025-12-31"
UMBRAL_VIX_PRINCIPAL = 30
UMBRAL_VIX_ADICIONAL = 25
CALENDARIO = "NYSE"  # Calendario común de sesiones; no es una fuente de precios.
CAPITAL_INICIAL_USD = 10_000.0
ROTULO_SIMULACION = "Simulación teórica con índices"
SUPUESTOS_SIMULACION = "Sin costos adicionales de rotación ni impuestos; SPY usa adjClose sin sumar dividendos"

SERIE_VIX = "VIX"
SERIE_REFERENCIA = "SPY"  # ETF: adjClose de Tiingo; no es un índice total return.
ESTRATEGIAS = ("PUT", "CNDR", "PPUT")
INVERSIONES = (*ESTRATEGIAS, SERIE_REFERENCIA)
SERIES_REQUERIDAS = (SERIE_VIX, *INVERSIONES)
ROTULO_CAIDA = "Máxima caída acumulada, medida con cierres mensuales"
CAMPO_CAIDA = "maxima_caida_acumulada_cierres_mensuales_pct"
EPISODIOS = ("2008_2009", "2020", "2022", "meses_restantes")

# PUT: venta de puts respaldada por letras del Tesoro; CNDR: iron condor;
# PPUT: S&P 500 con puts de protección. Se usan sus niveles publicados,
# sin reconstruir opciones ni agregar apalancamiento. VIX sólo clasifica.
# Formatos inspeccionados: coma, punto decimal, UTF-8, encabezado en fila 1.
# La correspondencia de campos fue indicada expresamente para este estudio.
FORMATOS = {
    "VIX": ("VIX.csv", "DATE", "CLOSE", "%m/%d/%Y", ["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]),
    "PUT": ("PUT.csv", "DATE", "PUT", "%m/%d/%Y", ["DATE", "PUT"]),
    "CNDR": ("CNDR.csv", "DATE", "CNDR", "%m/%d/%Y", ["DATE", "CNDR"]),
    "PPUT": ("PPUT.csv", "DATE", "PPUT", "%m/%d/%Y", ["DATE", "PPUT"]),
    "SPY": ("SPY_Tiingo.csv", "date", "adjClose", "%Y-%m-%d", ["date", "adjClose", "close", "divCash", "splitFactor"]),
}

RAIZ = Path(__file__).resolve().parent
CARPETA_DATOS = RAIZ / "datos_originales"
CARPETA_TABLAS = RAIZ / "resultados" / "tablas"
CARPETA_GRAFICOS = RAIZ / "resultados" / "graficos"
CARPETA_CONTROLES = RAIZ / "resultados" / "controles"


def guardar_csv(tabla: pd.DataFrame, destino: Path, *, indice: bool = False):
    """CSV con BOM para Excel, coma y punto decimal; ausentes como celdas vacías."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida = tabla.copy()
    # Pandas puede convertir Period(M) al fin de mes al aplicar date_format.
    # El identificador del mes no debe aparentar una fecha de cierre bursátil.
    if isinstance(salida.index, pd.PeriodIndex):
        salida.index = salida.index.astype(str)
    for columna in salida.columns:
        if isinstance(salida[columna].dtype, pd.PeriodDtype):
            salida[columna] = salida[columna].astype(str)
    salida.to_csv(destino, index=indice, encoding="utf-8-sig", date_format="%Y-%m-%d",
                  float_format="%.15g", na_rep="")


@dataclass
class Controles:
    """Registro explícito que acompaña al flujo, separado de los originales."""

    fuentes: list[dict] = field(default_factory=list)
    incidencias: list[dict] = field(default_factory=list)
    tablas: dict[str, pd.DataFrame] = field(default_factory=dict)
    archivos: dict[str, Path] = field(default_factory=dict)
    niveles: pd.DataFrame = field(default_factory=pd.DataFrame)
    fechas: pd.DataFrame = field(default_factory=pd.DataFrame)
    verificaciones: dict = field(default_factory=dict)

    def registrar(self, tipo, detalle, *, serie="", fecha="", archivo="", fila=None, valor=""):
        self.incidencias.append({
            "tipo": tipo, "serie": serie, "fecha": str(fecha), "archivo": archivo,
            "fila_csv": fila, "valor_original": valor, "detalle": detalle,
        })

    def guardar(self, estado: str, error: str | None = None):
        """Persiste también los diagnósticos si una validación detiene el proceso."""
        CARPETA_CONTROLES.mkdir(parents=True, exist_ok=True)
        for fuente in self.fuentes:
            serie = fuente["serie"]
            if not self.niveles.empty:
                fuente["cierres_validos"] = int(self.niveles[serie].notna().sum())
            diario = self.tablas.get("calendario_diario")
            if diario is not None:
                sesiones = diario.loc[diario["sesion_nyse"]]
                fuente["sesiones_nyse_esperadas"] = len(sesiones)
                fuente["observaciones_validas_nyse"] = int(sesiones[f"disponible_{serie}"].sum())
        guardar_csv(pd.DataFrame(self.fuentes), CARPETA_CONTROLES / "fuentes_verificadas.csv")
        columnas = ["tipo", "serie", "fecha", "archivo", "fila_csv", "valor_original", "detalle"]
        registros = list(self.incidencias)
        # Un registro de eventos reemplaza siete controles dispersos. Los
        # cierres se conservan aparte; calendario/cobertura se resumen por fuente.
        for nombre, tabla in self.tablas.items():
            if nombre in ("calendario_diario", "cierres_mensuales", "comparacion_cierres"):
                continue
            for fila in tabla.to_dict("records"):
                registros.append({
                    "tipo": nombre, "serie": fila.get("serie", fila.get("cartera", "")),
                    "fecha": fila.get("fecha", fila.get("mes", fila.get("primer_mes_incompleto", ""))),
                    "detalle": json.dumps({k: str(v) for k, v in fila.items()}, ensure_ascii=False),
                })
        incidencias = pd.DataFrame(registros, columns=columnas)
        guardar_csv(incidencias, CARPETA_CONTROLES / "incidencias.csv")
        guardar_csv(self.tablas.get("cierres_mensuales", pd.DataFrame(columns=["mes", "serie", "estado"])),
                    CARPETA_CONTROLES / "cierres_mensuales.csv")
        parametros = {
            "estado": estado, "error": error,
            "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
            "datos_desde": FECHA_INICIO_DATOS, "datos_hasta": FECHA_FIN_DATOS,
            "rendimientos_desde": FECHA_INICIO_ANALISIS, "rendimientos_hasta": FECHA_FIN_ANALISIS,
            "mes_base": str(pd.Period(FECHA_INICIO_DATOS, freq="M")),
            "benchmark": "SPY: ETF, cierre ajustado adjClose de SPY_Tiingo.csv",
            "umbral_principal": UMBRAL_VIX_PRINCIPAL, "umbral_sensibilidad": UMBRAL_VIX_ADICIONAL,
            "clasificacion": "alto si VIX del cierre del mes anterior >= umbral; bajo si <",
            "calendario_comun": CALENDARIO,
            "regla_cierre": "Exigir dato finito y positivo en la última sesión NYSE del mes",
            "imputacion": False, "desviacion_estandar_ddof": 1,
            "anualizacion": "CAGR = (capital final / capital inicial) ** (12 / meses) - 1; descriptivos sin anualizar",
            "comparacion_spy": "Media de diferencias en meses pareados; puntos porcentuales",
            "simulacion_carteras": {
                "rotulo": ROTULO_SIMULACION, "capital_inicial_usd": CAPITAL_INICIAL_USD,
                "supuestos": SUPUESTOS_SIMULACION, "aportes_y_retiros": False,
                "capitalizacion": "Capital anterior * (1 + rendimiento del activo asignado)",
                "faltantes": "Interrupción permanente por cartera; no rellenar ni saltar meses",
                "maxima_caida": ROTULO_CAIDA,
                "formula_caida": "Mínimo de capital / máximo acumulado - 1; incluye capital inicial",
                "frecuencia_maxima_caida": "mensual",
                "control_permanentes": "Capital inicial * nivel / nivel base, donde comparable; rtol=1e-12, atol=1e-8 USD",
            },
            "fuentes_precios": [f[0] for f in FORMATOS.values()],
            "incidencias_por_tipo": {str(k): int(v) for k, v in incidencias["tipo"].value_counts().items()},
            "filas_controles": {k: len(v) for k, v in self.tablas.items()},
            "verificaciones": self.verificaciones,
            "interpretacion": "Enfoque refinado después de observar primeros resultados; no acredita ejecución operativa ni desempeño fuera de muestra",
            "atribucion": "Producto de factores relativos de 2008-2009, 2020, 2022 y meses restantes; porcentajes no aditivos",
            "python": platform.python_version(),
            "dependencias": {nombre: version(nombre) for nombre in (
                "pandas", "numpy", "matplotlib", "pandas_market_calendars", "exchange_calendars", "tzdata"
            )},
            "sha256_codigo": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "sha256_requirements": hashlib.sha256((RAIZ / "requirements.txt").read_bytes()).hexdigest(),
            "salidas_sha256": {
                f"{carpeta.name}/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                for carpeta in (CARPETA_TABLAS, CARPETA_GRAFICOS, CARPETA_CONTROLES)
                for p in sorted(carpeta.glob("*"))
                if p.is_file() and p.name != "ejecucion.json"
            } if estado == "correcto" else {},
        }
        (CARPETA_CONTROLES / "ejecucion.json").write_text(
            json.dumps(parametros, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )


# 2. LOCALIZACIÓN Y CARGA
def buscar_archivos_originales() -> list[Path]:
    """Localiza sólo los cinco nombres autorizados; no abre otros archivos."""
    return [CARPETA_DATOS / formato[0] for formato in FORMATOS.values()
            if (CARPETA_DATOS / formato[0]).is_file()]


def cargar_datos(archivos: list[Path], controles: Controles | None = None) -> pd.DataFrame:
    """Lee campos y formatos explícitos. Fechas inválidas/duplicadas son fatales.

    Valores ausentes, no numéricos, no finitos o no positivos quedan como NaN,
    con el texto y la fila original registrados; nunca se imputan.
    """
    controles = controles if controles is not None else Controles()
    por_nombre = {p.name: p for p in archivos}
    faltantes = [f[0] for f in FORMATOS.values() if f[0] not in por_nombre]
    if faltantes:
        raise ValueError("Faltan archivos requeridos: " + ", ".join(faltantes))
    series = []
    for serie, (nombre, campo_fecha, campo_valor, formato_fecha, encabezado) in FORMATOS.items():
        archivo = por_nombre[nombre]
        contenido = archivo.read_bytes()
        controles.archivos[serie] = archivo
        fuente = {
            "serie": serie, "archivo": nombre, "campo": campo_valor,
            "tipo": "ETF con cierre ajustado" if serie == "SPY" else ("cierre VIX" if serie == "VIX" else "nivel de índice"),
            "sha256": hashlib.sha256(contenido).hexdigest(), "bytes": len(contenido),
            "separador": ",", "decimal": ".", "codificacion": "utf-8-sig",
            "formato_fecha": formato_fecha,
        }
        controles.fuentes.append(fuente)
        filas = list(csv.reader(io.StringIO(contenido.decode("utf-8-sig")), strict=True))
        if not filas or filas[0] != encabezado:
            raise ValueError(f"{nombre}: encabezado inesperado; se requiere {encabezado}.")
        for numero, fila in enumerate(filas[1:], start=2):
            if len(fila) != len(encabezado):
                raise ValueError(f"{nombre}, fila {numero}: cantidad de columnas incorrecta.")
        if len(filas) == 1:
            raise ValueError(f"{nombre}: no contiene observaciones.")
        bruto = pd.DataFrame(filas[1:], columns=encabezado)
        fuente["filas_leidas"] = len(bruto)
        fechas = pd.to_datetime(bruto[campo_fecha], format=formato_fecha, errors="coerce", exact=True)
        if fechas.isna().any():
            for i in bruto.index[fechas.isna()]:
                controles.registrar("fecha_invalida", "Se detiene; no se descarta la fila silenciosamente.",
                                    serie=serie, archivo=nombre, fila=int(i) + 2, valor=bruto.at[i, campo_fecha])
            raise ValueError(f"{nombre}: fecha inválida; consultar incidencias.csv.")
        duplicadas = fechas.duplicated(keep=False)
        fuente["filas_con_fecha_duplicada"] = int(duplicadas.sum())
        if duplicadas.any():
            for i in bruto.index[duplicadas]:
                controles.registrar("fecha_duplicada", "Se detiene sin elegir ni promediar duplicados.",
                                    serie=serie, archivo=nombre, fila=int(i) + 2, fecha=fechas[i].date())
            raise ValueError(f"{nombre}: fechas duplicadas; consultar incidencias.csv.")
        fuente.update({
            "fecha_inicial": str(fechas.min().date()), "fecha_final": str(fechas.max().date()),
            "orden_original_ascendente": bool(fechas.is_monotonic_increasing),
            "filas_en_periodo": int(fechas.between(FECHA_INICIO_DATOS, FECHA_FIN_DATOS).sum()),
        })
        fuente["filas_fuera_periodo"] = len(bruto) - fuente["filas_en_periodo"]
        if not fechas.is_monotonic_increasing:
            controles.registrar("reordenamiento", "Se ordena la copia de trabajo por fecha.", serie=serie, archivo=nombre)
        valores = pd.to_numeric(bruto[campo_valor], errors="coerce").astype(float)
        invalidos = ~np.isfinite(valores) | (valores <= 0)
        fuente["valores_invalidos"] = int(invalidos.sum())
        for i in bruto.index[invalidos]:
            controles.registrar("valor_invalido", "Ausente/no numérico/no finito/no positivo: se deja NaN.",
                                serie=serie, archivo=nombre, fila=int(i) + 2,
                                fecha=fechas[i].date(), valor=bruto.at[i, campo_valor])
        valores = valores.mask(invalidos)
        series.append(pd.Series(valores.to_numpy(), index=pd.DatetimeIndex(fechas), name=serie))
    return pd.concat(series, axis=1, sort=True).sort_index().rename_axis("fecha")


# 3. VALIDACIÓN Y TRAZABILIDAD
def sesiones_esperadas() -> pd.DatetimeIndex:
    """Calendario local de la biblioteca: feriados y cierres extraordinarios."""
    return mcal.get_calendar(CALENDARIO).valid_days(
        FECHA_INICIO_DATOS, FECHA_FIN_DATOS
    ).tz_localize(None).rename("fecha")


def validar_datos(datos_diarios: pd.DataFrame, controles: Controles | None = None) -> pd.DataFrame:
    """Valida una copia, registra exclusiones y reindexa sin rellenar.

    Una fecha fuera del calendario común no se declara errónea en su fuente.
    Valores iguales en sesiones consecutivas son alertas, no prueba de arrastre:
    se conservan, ya que eliminarlos podría borrar rendimientos reales de cero.
    """
    controles = controles if controles is not None else Controles()
    faltan = set(SERIES_REQUERIDAS) - set(datos_diarios.columns)
    if faltan:
        raise ValueError(f"Faltan series requeridas: {sorted(faltan)}")
    if not isinstance(datos_diarios.index, pd.DatetimeIndex) or datos_diarios.index.hasnans:
        raise ValueError("El índice debe contener fechas válidas.")
    if datos_diarios.index.has_duplicates:
        raise ValueError("Hay fechas duplicadas; no se deduplican automáticamente.")
    datos = datos_diarios.loc[:, list(SERIES_REQUERIDAS)].copy(deep=True)
    if not datos.index.is_monotonic_increasing:
        controles.registrar("reordenamiento", "Se ordena la copia de trabajo por fecha.")
    datos = datos.sort_index()
    for serie in SERIES_REQUERIDAS:
        numericos = pd.to_numeric(datos[serie], errors="coerce").astype(float)
        invalidos = datos[serie].notna() & (~np.isfinite(numericos) | (numericos <= 0))
        for fecha in datos.index[invalidos]:
            controles.registrar("valor_invalido", "Se excluye el valor y se deja NaN.",
                                serie=serie, fecha=fecha.date(), valor=str(datos.at[fecha, serie]))
        datos[serie] = numericos.mask(~np.isfinite(numericos) | (numericos <= 0))
    en_periodo = (datos.index >= FECHA_INICIO_DATOS) & (datos.index <= FECHA_FIN_DATOS)
    for serie in SERIES_REQUERIDAS:
        for fecha, valor in datos.loc[~en_periodo, serie].dropna().items():
            controles.registrar("fuera_periodo", "Excluido: datos de enero de 2007 a diciembre de 2025.",
                                serie=serie, archivo=FORMATOS[serie][0], fecha=fecha.date(), valor=float(valor))
    datos = datos.loc[en_periodo]
    sesiones = sesiones_esperadas()
    comparacion = datos.reindex(datos.index.union(sesiones)).notna().add_prefix("disponible_")
    comparacion.insert(0, "sesion_nyse", comparacion.index.isin(sesiones))
    controles.tablas["calendario_diario"] = comparacion.rename_axis("fecha").reset_index()
    extras = datos.index.difference(sesiones)
    for serie in SERIES_REQUERIDAS:
        for fecha, valor in datos.loc[extras, serie].dropna().items():
            controles.registrar("fuera_calendario_comun", "Se excluye de la muestra común; no implica error de origen.",
                                serie=serie, archivo=FORMATOS[serie][0], fecha=fecha.date(), valor=float(valor))
    datos = datos.reindex(sesiones)  # Sólo NaN donde no hay dato; sin ffill/bfill/interpolación.
    faltantes, repetidos = [], []
    for serie in SERIES_REQUERIDAS:
        for fecha in datos.index[datos[serie].isna()]:
            faltantes.append({"fecha": fecha, "serie": serie, "motivo": "Sesión esperada sin valor válido; no imputado"})
        iguales = datos[serie].eq(datos[serie].shift(1)) & datos[serie].notna()
        for fecha in datos.index[iguales]:
            repetidos.append({"fecha": fecha, "serie": serie, "nivel": datos.at[fecha, serie],
                              "decision": "Conservar; igualdad no demuestra arrastre"})
    controles.tablas["faltantes_diarios"] = pd.DataFrame(faltantes, columns=["fecha", "serie", "motivo"])
    controles.tablas["valores_repetidos"] = pd.DataFrame(repetidos, columns=["fecha", "serie", "nivel", "decision"])
    if datos.notna().sum().eq(0).any():
        raise ValueError("Hay una serie sin valores válidos en el período y calendario requeridos.")
    return datos


# 4. CIERRES Y RENDIMIENTOS MENSUALES
def obtener_cierres_mensuales(datos_diarios: pd.DataFrame, controles: Controles | None = None):
    """Exige el dato de la última sesión esperada, sin usar un cierre anterior.

    Devuelve niveles y fechas reales, sobre TODOS los meses del período.
    Los faltantes intrames se documentan, pero no invalidan cierres presentes.
    """
    meses = pd.period_range(FECHA_INICIO_DATOS, FECHA_FIN_DATOS, freq="M", name="mes")
    sesiones = sesiones_esperadas()
    fechas_esperadas = pd.Series(sesiones, index=sesiones.to_period("M")).groupby(level=0).max().reindex(meses)
    observados = datos_diarios.reindex(sesiones)
    observados = observados.where(np.isfinite(observados) & (observados > 0))
    niveles = observados.reindex(pd.DatetimeIndex(fechas_esperadas)).copy()
    niveles.index = meses
    fechas = pd.DataFrame({serie: fechas_esperadas.where(niveles[serie].notna()) for serie in SERIES_REQUERIDAS})
    if controles is not None:
        detalle = []
        for mes in meses:
            datos_mes = observados.loc[observados.index.to_period("M") == mes]
            for serie in SERIES_REQUERIDAS:
                validos = datos_mes[serie].dropna()
                detalle.append({
                    "mes": str(mes), "serie": serie, "fecha_cierre_esperada": fechas_esperadas[mes],
                    "ultima_fecha_disponible": validos.index.max() if len(validos) else pd.NaT,
                    "fecha_cierre_usada": fechas.at[mes, serie], "nivel_usado": niveles.at[mes, serie],
                    "sesiones_esperadas": len(datos_mes), "observaciones_validas": len(validos),
                    "faltantes_intrames": len(datos_mes) - len(validos),
                    "estado": "ok" if pd.notna(niveles.at[mes, serie]) else "sin_cierre_valido",
                })
        controles.tablas["cierres_mensuales"] = pd.DataFrame(detalle)
        comparacion = fechas.add_prefix("fecha_").copy()
        comparacion.insert(0, "fecha_esperada", fechas_esperadas)
        comparacion["cantidad_cierres_validos"] = niveles.notna().sum(axis=1)
        comparacion["cinco_cierres_alineados"] = fechas.eq(fechas_esperadas, axis=0).all(axis=1)
        controles.tablas["comparacion_cierres"] = comparacion.reset_index()
        controles.niveles, controles.fechas = niveles, fechas
    return niveles, fechas


def calcular_rendimientos_mensuales(datos_diarios: pd.DataFrame, controles: Controles | None = None) -> pd.DataFrame:
    """r[t] = nivel[t] / nivel[t-1] - 1, sobre meses consecutivos.

    Enero de 2007 es base; la salida va de febrero de 2007 a diciembre de
    2025 (227 meses). Un mes sin cierre invalida ese retorno y el siguiente.
    """
    niveles, _ = obtener_cierres_mensuales(datos_diarios, controles)
    inversiones = niveles.loc[:, list(INVERSIONES)]
    rendimientos = inversiones.div(inversiones.shift(1)).sub(1)
    rendimientos = rendimientos.loc[pd.Period(FECHA_INICIO_ANALISIS, freq="M"):pd.Period(FECHA_FIN_ANALISIS, freq="M")]
    if controles is not None:
        exclusiones = []
        for mes in rendimientos.index:
            for serie in INVERSIONES:
                if pd.isna(rendimientos.at[mes, serie]):
                    motivos = []
                    if pd.isna(niveles.at[mes, serie]):
                        motivos.append("falta cierre válido del mes")
                    if mes - 1 not in niveles.index or pd.isna(niveles.at[mes - 1, serie]):
                        motivos.append("falta cierre válido del mes anterior")
                    exclusiones.append({"mes": str(mes), "serie": serie, "motivo": "; ".join(motivos)})
        controles.tablas["exclusiones_rendimientos"] = pd.DataFrame(exclusiones, columns=["mes", "serie", "motivo"])
    return rendimientos


# 5. CLASIFICACIÓN SEGÚN EL VIX PREVIO
def clasificar_por_vix(datos_diarios, rendimientos_mensuales, umbral: float,
                       controles: Controles | None = None) -> pd.DataFrame:
    """Febrero usa VIX de enero; alto incluye la igualdad. NaN queda sin grupo."""
    if not np.isfinite(umbral) or umbral <= 0:
        raise ValueError("El umbral VIX debe ser finito y positivo.")
    niveles, fechas = obtener_cierres_mensuales(datos_diarios)
    tabla = rendimientos_mensuales.copy()
    tabla["vix_previo"] = niveles[SERIE_VIX].shift(1).reindex(tabla.index)
    tabla["fecha_vix_previo"] = fechas[SERIE_VIX].shift(1).reindex(tabla.index)
    tabla["grupo"] = pd.Series(pd.NA, index=tabla.index, dtype="string")
    tabla.loc[tabla["vix_previo"] >= umbral, "grupo"] = "alto"
    tabla.loc[tabla["vix_previo"] < umbral, "grupo"] = "bajo"
    if controles is not None:
        sin_vix = tabla.loc[tabla["grupo"].isna()]
        controles.tablas[f"exclusiones_clasificacion_vix_{umbral:g}"] = pd.DataFrame(
            [{"mes": str(mes), "umbral": umbral, "motivo": "Falta cierre VIX válido del mes anterior"}
             for mes in sin_vix.index], columns=["mes", "umbral", "motivo"]
        )
    return tabla


# 6. TABLAS, GRÁFICOS Y CONTROLES
def calcular_metricas(tabla: pd.DataFrame, umbral: float) -> pd.DataFrame:
    """Métricas mensuales en %, diferencias pareadas en pp y n explícitos."""
    filas = []
    for grupo in ("bajo", "alto"):
        muestra = tabla.loc[tabla["grupo"] == grupo]
        for serie in INVERSIONES:
            valores = muestra[serie].dropna()
            pares = muestra[serie].notna() & muestra[SERIE_REFERENCIA].notna()
            diferencia = muestra.loc[pares, serie] - muestra.loc[pares, SERIE_REFERENCIA]
            n = len(valores)
            filas.append({
                "umbral_vix": umbral, "grupo": grupo, "serie": serie,
                "cantidad_observaciones": n,
                "rendimiento_medio_pct": 100 * valores.mean() if n else np.nan,
                "mediana_pct": 100 * valores.median() if n else np.nan,
                "desviacion_estandar_pct": 100 * valores.std(ddof=1) if n >= 2 else np.nan,
                "porcentaje_meses_negativos": 100 * valores.lt(0).sum() / n if n else np.nan,
                "peor_rendimiento_mensual_pct": 100 * valores.min() if n else np.nan,
                "diferencia_media_vs_spy_pp": 100 * diferencia.mean() if len(diferencia) else np.nan,
                "cantidad_pares_vs_spy": int(pares.sum()),
            })
    return pd.DataFrame(filas)


def simular_carteras(tabla: pd.DataFrame, umbral: float):
    """Capitaliza siete carteras principales o tres de sensibilidad, sin aportes ni retiros.

    vix_previo ya contiene la señal del mes anterior: no se vuelve a desplazar.
    Cada regla mantiene su índice fijo y usa SPY cuando no está activada.
    Un faltante necesario interrumpe la cadena; nunca se reanuda tras el hueco.
    Las cuatro carteras permanentes no requieren señal. Devuelve capitales, asignaciones y resumen.
    """
    if not np.isfinite(umbral) or umbral <= 0:
        raise ValueError("El umbral VIX debe ser finito y positivo.")
    if not np.isfinite(CAPITAL_INICIAL_USD) or CAPITAL_INICIAL_USD <= 0:
        raise ValueError("El capital inicial debe ser finito y positivo.")
    if not isinstance(tabla.index, pd.PeriodIndex) or tabla.index.freqstr != "M" or tabla.index.hasnans:
        raise ValueError("La simulación requiere un índice de meses válidos (PeriodIndex M).")
    if tabla.index.has_duplicates:
        raise ValueError("La simulación contiene meses duplicados; no se deduplican.")
    meses = pd.period_range(FECHA_INICIO_ANALISIS, FECHA_FIN_ANALISIS, freq="M", name="mes")
    mes_base = pd.Period(FECHA_INICIO_DATOS, freq="M")
    if not len(meses) or meses[0] != mes_base + 1:
        raise ValueError("Los rendimientos deben comenzar el mes siguiente a la base.")
    calendario = pd.period_range(mes_base, meses[-1], freq="M", name="mes")
    datos = tabla.reindex(meses).copy()  # Ordena e incluye meses ausentes con NaN.
    for columna in (*INVERSIONES, "vix_previo"):
        datos[columna] = pd.to_numeric(datos.get(columna, pd.Series(index=meses, dtype=float)), errors="coerce").astype(float)
    carteras = [(f"{serie}_VIX_ALTO_{umbral:g}", serie, "alto") for serie in ESTRATEGIAS]
    if umbral == UMBRAL_VIX_PRINCIPAL:
        carteras = [(f"SIEMPRE_{serie}", serie, None) for serie in (SERIE_REFERENCIA, *ESTRATEGIAS)] + carteras
    capitales = pd.DataFrame(np.nan, index=calendario, columns=[c[0] for c in carteras])
    capitales.loc[mes_base] = CAPITAL_INICIAL_USD
    asignaciones, resumen = [], []
    for cartera, indice, activacion in carteras:
        capital_anterior = CAPITAL_INICIAL_USD
        primer_faltante, causa_inicial = "", ""
        meses_capitalizados = 0
        for mes in meses:
            # .at conserva el tipo de cada columna incluso en una fila vacía.
            senal = datos.at[mes, "vix_previo"]
            senal_valida = np.isfinite(senal) and senal > 0
            grupo = ("alto" if senal >= umbral else "bajo") if senal_valida else pd.NA
            activo, problema = indice if activacion is None else SERIE_REFERENCIA, ""
            if activacion is not None:
                if not senal_valida:
                    activo, problema = pd.NA, "Falta señal VIX previa válida"
                elif grupo == activacion:
                    activo = indice
            rendimiento = float(datos.at[mes, activo]) if pd.notna(activo) else np.nan
            if not problema and (not np.isfinite(rendimiento) or rendimiento < -1):
                problema = f"Falta rendimiento válido de {activo}"
            capital, aplicado = np.nan, np.nan
            if not primer_faltante and not problema:
                candidato = float(capital_anterior) * (1 + rendimiento)
                if np.isfinite(candidato):
                    capital, aplicado = candidato, rendimiento
                    capital_anterior = capital
                    capitales.at[mes, cartera] = capital
                    meses_capitalizados += 1
                else:
                    problema = "Capital calculado no finito"
            if not primer_faltante and problema:
                primer_faltante, causa_inicial = str(mes), problema
            if primer_faltante:
                motivo = problema or f"Capital previo indeterminado desde {primer_faltante}: {causa_inicial}"
            else:
                motivo = ""
            asignaciones.append({
                "mes": str(mes), "umbral_vix": umbral if activacion else np.nan, "cartera": cartera,
                "indice_asignado": indice,
                "vix_previo": senal,
                "fecha_vix_previo": datos.at[mes, "fecha_vix_previo"] if "fecha_vix_previo" in datos else pd.NaT,
                "grupo": grupo, "activo_asignado": activo, "rendimiento_activo": rendimiento,
                "rendimiento_aplicado": aplicado, "capital_usd": capital,
                "estado": "incompleta" if primer_faltante else "calculado", "motivo": motivo,
                "simulacion": ROTULO_SIMULACION,
            })
        completa = not primer_faltante
        curva = capitales[cartera]  # Incluye el capital inicial en el máximo acumulado.
        capital_final = curva.iloc[-1] if completa else np.nan
        caida = curva.div(curva.cummax()).sub(1).min() if completa else np.nan
        resumen.append({
            "analisis": "principal" if umbral == UMBRAL_VIX_PRINCIPAL else "sensibilidad",
            "umbral_vix": umbral if activacion else np.nan, "cartera": cartera, "indice_asignado": indice,
            "regimen_activacion": activacion or "siempre", "capital_inicial_usd": CAPITAL_INICIAL_USD,
            "capital_final_usd": capital_final,
            "rendimiento_acumulado_pct": 100 * (capital_final / CAPITAL_INICIAL_USD - 1),
            "rendimiento_anual_compuesto_pct": 100 * ((capital_final / CAPITAL_INICIAL_USD) ** (12 / len(meses)) - 1),
            CAMPO_CAIDA: 100 * caida,
            "estado": "completa" if completa else "incompleta", "meses_esperados": len(meses),
            "meses_capitalizados": meses_capitalizados, "primer_mes_incompleto": primer_faltante,
            "motivo_incompleta": causa_inicial, "simulacion": ROTULO_SIMULACION,
            "supuestos": SUPUESTOS_SIMULACION,
        })
    return capitales, pd.DataFrame(asignaciones), pd.DataFrame(resumen)


def calcular_aporte_episodios(asignaciones: pd.DataFrame, rendimientos: pd.DataFrame) -> pd.DataFrame:
    """Atribución multiplicativa; restos es una agrupación sin drawdown propio."""
    filas = []
    meses = rendimientos.index
    grupos = pd.Series("meses_restantes", index=meses)
    grupos.loc[(meses.year >= 2008) & (meses.year <= 2009)] = "2008_2009"
    for anio in (2020, 2022):
        grupos.loc[meses.year == anio] = str(anio)
    condicionales = asignaciones.loc[asignaciones["cartera"].str.contains("_VIX_ALTO_")]
    for cartera, datos in condicionales.groupby("cartera", sort=False):
        umbral = datos["umbral_vix"].iloc[0]
        indice = datos["indice_asignado"].iloc[0]
        datos = datos.set_index(pd.PeriodIndex(datos["mes"], freq="M")).reindex(meses)
        for episodio in EPISODIOS:
            seleccion = grupos.eq(episodio)
            r = datos.loc[seleccion, "rendimiento_aplicado"]
            spy = rendimientos.loc[seleccion, "SPY"]
            validos = np.isfinite(r) & r.ge(-1) & np.isfinite(spy) & spy.gt(-1)
            completo = bool(validos.all())
            factor_cartera = (1 + r).prod(skipna=False) if completo else np.nan
            factor_spy = (1 + spy).prod(skipna=False) if completo else np.nan
            factor = factor_cartera / factor_spy if completo else np.nan
            filas.append({
                "analisis": "principal" if umbral == UMBRAL_VIX_PRINCIPAL else "sensibilidad",
                "cartera": cartera, "umbral_vix": umbral, "episodio": episodio,
                "cantidad_meses": len(r), "meses_validos_pareados": int(validos.sum()),
                "meses_indice_activo": int(datos.loc[seleccion, "activo_asignado"].eq(indice).sum()),
                "factor_cartera": factor_cartera, "factor_spy": factor_spy,
                "factor_relativo": factor, "ventaja_relativa_pct": 100 * (factor - 1),
                "estado": ("completa" if len(r) else "sin_meses") if completo else "incompleta",
            })
    return pd.DataFrame(filas)


def verificar_resultados(mensuales, capitales, resumen, episodios):
    """Reconstruye desde las tablas exportadas; no utiliza la función simuladora."""
    def iguales(actual, esperado, nombre, atol=1e-12):
        if not np.allclose(actual, esperado, rtol=1e-12, atol=atol, equal_nan=True):
            raise ValueError(f"No se cumple la identidad: {nombre}")

    meses = pd.period_range(FECHA_INICIO_DATOS, FECHA_FIN_DATOS, freq="M", name="mes")
    if not mensuales.index.equals(meses) or not capitales.index.equals(meses):
        raise ValueError("El calendario mensual exportado no está completo y ordenado.")
    iguales(mensuales["vix_previo"], mensuales["nivel_VIX"].shift(1), "VIX del mes previo")
    fecha_previa = pd.to_datetime(mensuales["fecha_vix_previo"])
    fecha_esperada = pd.to_datetime(mensuales["fecha_cierre_VIX"]).shift(1)
    if not fecha_previa.equals(fecha_esperada.rename("fecha_vix_previo")):
        raise ValueError("La fecha de la señal no es la del cierre VIX anterior.")
    for serie in INVERSIONES:
        niveles = mensuales[f"nivel_{serie}"]
        iguales(mensuales[f"retorno_{serie}"], niveles / niveles.shift(1) - 1, f"retornos {serie}")
    for fila in resumen.to_dict("records"):
        cartera, indice = fila["cartera"], fila["indice_asignado"]
        condicional = fila["regimen_activacion"] == "alto"
        curva, retornos, activos = [CAPITAL_INICIAL_USD], [], []
        for _, mes in mensuales.iloc[1:].iterrows():
            senal = mes["vix_previo"]
            activo = indice if not condicional or senal >= fila["umbral_vix"] else "SPY"
            r = mes[f"retorno_{activo}"]
            if condicional and (not np.isfinite(senal) or senal <= 0):
                r = np.nan
            if not np.isfinite(r) or r < -1 or not np.isfinite(curva[-1]):
                r = np.nan
            retornos.append(r)
            activos.append(activo)
            curva.append(curva[-1] * (1 + r))
        curva = np.asarray(curva)
        iguales(capitales[cartera], curva, f"capitalización {cartera}", atol=1e-8)
        completa = bool(np.isfinite(curva).all())
        if fila["estado"] != ("completa" if completa else "incompleta"):
            raise ValueError(f"Estado incorrecto para {cartera}.")
        n = len(retornos)
        if fila["meses_esperados"] != n or fila["meses_capitalizados"] != np.isfinite(curva[1:]).sum():
            raise ValueError(f"Cantidad de meses inconsistente para {cartera}.")
        valores = [curva[-1], 100 * (curva[-1] / curva[0] - 1),
                   100 * ((curva[-1] / curva[0]) ** (12 / n) - 1),
                   100 * np.min(curva / np.maximum.accumulate(curva) - 1)] if completa else [np.nan] * 4
        iguales([fila[c] for c in ("capital_final_usd", "rendimiento_acumulado_pct",
                "rendimiento_anual_compuesto_pct", CAMPO_CAIDA)], valores, f"métricas {cartera}", atol=1e-8)
        if not condicional:
            base = mensuales[f"nivel_{indice}"].iloc[0]
            referencia = CAPITAL_INICIAL_USD * mensuales[f"nivel_{indice}"] / base
            validos = np.isfinite(curva)
            # El capital inicial no necesita nivel; se compara cuando existe base.
            if np.isfinite(base):
                iguales(curva[validos], referencia[validos], f"nivel normalizado {indice}", atol=1e-8)
            continue
        grupos = episodios.loc[episodios["cartera"] == cartera].set_index("episodio")
        if set(grupos.index) != set(EPISODIOS) or len(grupos) != 4 or grupos["cantidad_meses"].sum() != n:
            raise ValueError(f"Partición incompleta de episodios: {cartera}")
        anios = meses[1:].year
        mascaras = [(anios >= 2008) & (anios <= 2009), anios == 2020, anios == 2022]
        mascaras.append(~np.logical_or.reduce(mascaras))
        spy = mensuales["retorno_SPY"].iloc[1:].to_numpy()
        for nombre, mascara in zip(EPISODIOS, mascaras):
            grupo = grupos.loc[nombre]
            r = np.asarray(retornos)[mascara]
            s = spy[mascara]
            completo = bool(np.isfinite(r).all() and np.isfinite(s).all() and (s > -1).all())
            fc = np.prod(1 + r) if completo else np.nan
            fs = np.prod(1 + s) if completo else np.nan
            iguales(grupo[["factor_cartera", "factor_spy", "factor_relativo", "ventaja_relativa_pct"]].astype(float),
                    [fc, fs, fc / fs, 100 * (fc / fs - 1)], f"episodio {cartera}/{nombre}")
            if grupo["cantidad_meses"] != int(mascara.sum()):
                raise ValueError(f"Meses de episodio incorrectos: {cartera}/{nombre}")
        if completa and capitales["SIEMPRE_SPY"].notna().all():
            iguales(grupos["factor_relativo"].prod(skipna=False),
                    curva[-1] / capitales["SIEMPRE_SPY"].iloc[-1], f"producto de episodios {cartera}")
    return {
        "identidades_capitalizacion": "verificadas en todos los meses y carteras",
        "senal_y_fecha_vix_previo": "verificadas", "metricas": "verificadas",
        "atribucion_por_episodios": "verificada sin sumar porcentajes",
        "cierres_esperados": len(meses), "rendimientos_esperados": len(meses) - 1,
        "cierres_validos_por_serie": {s: int(mensuales[f"nivel_{s}"].notna().sum()) for s in SERIES_REQUERIDAS},
        "rendimientos_validos_por_serie": {s: int(mensuales[f"retorno_{s}"].notna().sum()) for s in INVERSIONES},
        "carteras_completas": int(resumen["estado"].eq("completa").sum()),
        "carteras_incompletas": int(resumen["estado"].eq("incompleta").sum()),
        "tolerancia": "rtol=1e-12; atol=1e-8 USD/métricas y 1e-12 factores",
    }


def guardar_graficos(diarios, capitales, resumen):
    """Tres PNG vigentes; las curvas provienen del CSV ya exportado y verificado."""
    CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    colores = {"SPY": "#334155", "PUT": "#008577", "CNDR": "#3574ba", "PPUT": "#ba7519"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.18, "axes.axisbelow": True,
                         "savefig.dpi": 160, "figure.facecolor": "white"})
    def terminar(fig, nombre, nota, rect):
        for ax in fig.axes:
            ax.xaxis.set_major_locator(mdates.YearLocator(2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax.set_xlim(pd.Timestamp(FECHA_INICIO_DATOS), pd.Timestamp(FECHA_FIN_DATOS))
        fig.text(0.08, 0.016, nota, fontsize=9, color="#555555")
        fig.tight_layout(rect=rect)
        fig.savefig(CARPETA_GRAFICOS / nombre)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(diarios.index, diarios["VIX"], color=colores["SPY"], lw=0.85, label="VIX · cierre diario")
    for umbral, color, texto in [(30, "#ba493f", "Principal"), (25, "#ba7519", "Sensibilidad")]:
        ax.axhline(umbral, color=color, ls="--", lw=1.3, label=f"{texto}: {umbral}")
    ax.set(title="VIX diario y umbrales de activación · 2007–2025", ylabel="VIX (puntos)", xlabel="Fecha")
    ax.legend(loc="upper right", frameon=False)
    terminar(fig, "01_vix_umbrales.png", "Calendario común NYSE. La cartera mensual utiliza el cierre VIX del mes anterior.", (0, 0.05, 1, 1))

    fechas = pd.to_datetime(capitales["fecha_cierre_esperada"])
    estados = resumen.set_index("cartera")["estado"]
    def etiqueta(nombre, texto):
        return texto + (" (incompleta)" if estados[nombre] == "incompleta" else "")

    fig, ejes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, sharey=True)
    for ax, serie in zip(ejes, ESTRATEGIAS):
        for nombre, color, estilo, texto in [
            ("SIEMPRE_SPY", colores["SPY"], "-", "Siempre SPY"),
            (f"SIEMPRE_{serie}", colores[serie], "--", f"Siempre {serie}"),
            (f"{serie}_VIX_ALTO_30", colores[serie], "-", f"{serie} si VIX previo ≥ 30; SPY el resto"),
        ]:
            ax.plot(fechas, capitales[nombre], color=color, ls=estilo, lw=1.6, label=etiqueta(nombre, texto))
        ax.set(title=serie, ylabel="Capital (USD)")
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    ejes[-1].set_xlabel("Fecha de cierre mensual")
    fig.suptitle("Capital de las carteras · umbral principal VIX ≥ 30", fontsize=15)
    terminar(fig, "02_capitales_vix_30.png", "USD 10.000 al cierre de enero de 2007. Simulación teórica sin costos adicionales de rotación ni impuestos.", (0, 0.035, 1, 0.97))

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for serie in ("SPY", *ESTRATEGIAS):
        nombre = "SIEMPRE_SPY" if serie == "SPY" else f"{serie}_VIX_ALTO_30"
        curva = capitales[nombre]
        texto = "Siempre SPY" if serie == "SPY" else f"{serie} condicional"
        ax.plot(fechas, 100 * (curva / curva.cummax() - 1), color=colores[serie], lw=1.3, label=etiqueta(nombre, texto))
    ax.set(title="Caídas desde máximos · SPY y carteras con VIX previo ≥ 30",
           ylabel="Caída desde el máximo acumulado (%)", xlabel="Fecha de cierre mensual")
    ax.legend(loc="lower right", frameon=False)
    terminar(fig, "03_caidas_vix_30.png", ROTULO_CAIDA + ". Incluye el capital inicial.", (0, 0.06, 1, 1))


def main() -> int:
    """Único flujo vigente; actualiza siempre los mismos cinco CSV y tres PNG."""
    controles = Controles()
    try:
        controles.guardar("en_curso")
        diarios = validar_datos(cargar_datos(buscar_archivos_originales(), controles), controles)
        rendimientos = calcular_rendimientos_mensuales(diarios, controles)
        mensuales = controles.niveles.add_prefix("nivel_").join(controles.fechas.add_prefix("fecha_cierre_"))
        mensuales.insert(0, "fecha_cierre_esperada", controles.tablas["comparacion_cierres"].set_index("mes")["fecha_esperada"])
        mensuales = mensuales.join(rendimientos.add_prefix("retorno_"))
        capitales_lista, asignaciones_lista, resumenes, descriptivos = [], [], [], []
        for umbral in (UMBRAL_VIX_PRINCIPAL, UMBRAL_VIX_ADICIONAL):
            tabla = clasificar_por_vix(diarios, rendimientos, umbral, controles)
            if umbral == UMBRAL_VIX_PRINCIPAL:
                mensuales = mensuales.join(tabla[["vix_previo", "fecha_vix_previo"]])
            mensuales[f"regimen_{umbral}"] = tabla["grupo"]
            capitales, asignaciones, resumen = simular_carteras(tabla, umbral)
            capitales_lista.append(capitales)
            asignaciones_lista.append(asignaciones)
            resumenes.append(resumen)
            descriptivo = calcular_metricas(tabla, umbral)
            descriptivo.insert(0, "analisis", "principal" if umbral == UMBRAL_VIX_PRINCIPAL else "sensibilidad")
            descriptivos.append(descriptivo)
        capitales = pd.concat(capitales_lista, axis=1)
        capitales.insert(0, "fecha_cierre_esperada", mensuales["fecha_cierre_esperada"])
        asignaciones = pd.concat(asignaciones_lista, ignore_index=True)
        resumen = pd.concat(resumenes, ignore_index=True)
        episodios = calcular_aporte_episodios(asignaciones, rendimientos)
        controles.tablas["simulaciones_incompletas"] = resumen.loc[resumen["estado"].eq("incompleta")]
        for nombre, tabla, indice in [
            ("datos_mensuales", mensuales, True), ("capitales_mensuales", capitales, True),
            ("comparacion_carteras", resumen, False), ("aporte_episodios", episodios, False),
            ("descriptivos_regimen", pd.concat(descriptivos, ignore_index=True), False),
        ]:
            guardar_csv(tabla, CARPETA_TABLAS / f"{nombre}.csv", indice=indice)

        def leer(nombre, mensual=False):
            tabla = pd.read_csv(CARPETA_TABLAS / f"{nombre}.csv")
            if mensual:
                tabla.index = pd.PeriodIndex(tabla.pop("mes"), freq="M", name="mes")
            return tabla
        mensuales, capitales = leer("datos_mensuales", True), leer("capitales_mensuales", True)
        resumen, episodios = leer("comparacion_carteras"), leer("aporte_episodios")
        controles.verificaciones = verificar_resultados(mensuales, capitales, resumen, episodios)
        controles.verificaciones["regimenes"] = {
            str(u): {g: int(mensuales[f"regimen_{u}"].eq(g).sum()) for g in ("alto", "bajo")}
            for u in (UMBRAL_VIX_PRINCIPAL, UMBRAL_VIX_ADICIONAL)
        }
        controles.verificaciones["graficos"] = "Curvas construidas desde capitales_mensuales.csv exportado y verificado; VIX desde sesiones diarias validadas"
        guardar_graficos(diarios, capitales, resumen)
        for fuente in controles.fuentes:
            fuente["sha256_final"] = hashlib.sha256(controles.archivos[fuente["serie"]].read_bytes()).hexdigest()
            fuente["original_sin_cambios"] = fuente["sha256_final"] == fuente["sha256"]
            if not fuente["original_sin_cambios"]:
                raise ValueError(f"Cambió el original: {fuente['archivo']}")
        controles.guardar("correcto")
    except (OSError, ValueError, csv.Error, AssertionError) as error:
        controles.guardar("error", str(error))
        print(f"Análisis detenido: {error}. Consultar {CARPETA_CONTROLES / 'ejecucion.json'}")
        return 1
    print(f"Verificado: {len(mensuales)} cierres; {len(rendimientos)} meses de rendimientos.")
    print(f"Carteras completas: {resumen['estado'].eq('completa').sum()}/{len(resumen)}.")
    print(f"Faltantes diarios sin imputar: {len(controles.tablas['faltantes_diarios'])}.")
    print("Cinco tablas, tres gráficos y cuatro controles. Originales sin cambios (SHA-256).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


