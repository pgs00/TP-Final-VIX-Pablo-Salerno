"""Pruebas de los controles que evitan sesgos y rendimientos espurios.

Las muestras artificiales se usan sólo aquí; el análisis usa los cinco CSV.
"""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import analisis as a


class LecturaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        contenidos = {
            "VIX.csv": "DATE,OPEN,HIGH,LOW,CLOSE\n01/03/2007,10,20,9,12\n",
            "PUT.csv": "DATE,PUT\n01/03/2007,100\n",
            "CNDR.csv": "DATE,CNDR\n01/03/2007,200\n",
            "PPUT.csv": "DATE,PPUT\n01/03/2007,300\n",
            "SPY_Tiingo.csv": (
                "date,adjClose,close,divCash,splitFactor\n"
                "2007-01-03,98.8,141.37,0,1\n"
            ),
        }
        for nombre, contenido in contenidos.items():
            (self.raiz / nombre).write_text(contenido, encoding="utf-8")

    def cargar(self):
        return a.cargar_datos(list(self.raiz.glob("*.csv")))

    def test_usa_adjclose_y_fecha_estadounidense_sin_tocar_originales(self):
        antes = {p.name: p.read_bytes() for p in self.raiz.iterdir()}
        datos = self.cargar()
        self.assertEqual(datos.loc[pd.Timestamp("2007-01-03"), "SPY"], 98.8)
        self.assertEqual(datos.loc[pd.Timestamp("2007-01-03"), "VIX"], 12)
        self.assertEqual(antes, {p.name: p.read_bytes() for p in self.raiz.iterdir()})

    def test_duplicado_detiene_sin_elegir_una_fila(self):
        with (self.raiz / "PUT.csv").open("a", encoding="utf-8") as archivo:
            archivo.write("01/03/2007,101\n")
        with self.assertRaisesRegex(ValueError, "duplicad"):
            self.cargar()

    def test_fecha_invalida_no_desaparece_silenciosamente(self):
        (self.raiz / "CNDR.csv").write_text(
            "DATE,CNDR\n01/32/2007,200\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "fecha"):
            self.cargar()

    def test_falta_un_archivo_no_se_sustituye(self):
        (self.raiz / "SPY_Tiingo.csv").unlink()
        with self.assertRaisesRegex(ValueError, "SPY_Tiingo"):
            self.cargar()


class MetodologiaTest(unittest.TestCase):
    def setUp(self):
        parametros = patch.multiple(
            a,
            FECHA_INICIO_DATOS="2007-01-01",
            FECHA_FIN_DATOS="2007-04-30",
            FECHA_INICIO_ANALISIS="2007-02-01",
            FECHA_FIN_ANALISIS="2007-04-30",
        )
        parametros.start()
        self.addCleanup(parametros.stop)
        fechas = pd.to_datetime(["2007-01-31", "2007-02-28", "2007-03-30", "2007-04-30"])
        self.datos = pd.DataFrame(
            {"VIX": [30, 25, 19, 80], **{
                serie: [100, 110, 121, 133.1] for serie in ("PUT", "CNDR", "PPUT", "SPY")
            }}, index=fechas, dtype=float,
        )

    def test_mes_ausente_no_produce_retorno_de_varios_meses(self):
        datos = self.datos.drop(pd.Timestamp("2007-02-28"))
        rend = a.calcular_rendimientos_mensuales(datos)
        self.assertEqual(list(rend.index.astype(str)), ["2007-02", "2007-03", "2007-04"])
        self.assertTrue(rend.loc["2007-02", "PUT"] != rend.loc["2007-02", "PUT"])
        self.assertTrue(pd.isna(rend.loc["2007-03", "PUT"]))
        self.assertAlmostEqual(rend.loc["2007-04", "PUT"], 0.1)

    def test_ultimo_dato_de_mes_incompleto_no_es_cierre(self):
        datos = self.datos.rename(index={pd.Timestamp("2007-02-28"): pd.Timestamp("2007-02-27")})
        rend = a.calcular_rendimientos_mensuales(datos)
        self.assertTrue(pd.isna(rend.loc["2007-02", "SPY"]))
        self.assertTrue(pd.isna(rend.loc["2007-03", "SPY"]))

    def test_vix_previo_incluye_igualdad_y_no_mira_el_mes_actual(self):
        rend = a.calcular_rendimientos_mensuales(self.datos)
        principal = a.clasificar_por_vix(self.datos, rend, 30)
        sensibilidad = a.clasificar_por_vix(self.datos, rend, 25)
        self.assertEqual(principal["vix_previo"].tolist(), [30, 25, 19])
        self.assertEqual(principal["grupo"].tolist(), ["alto", "bajo", "bajo"])
        self.assertEqual(sensibilidad["grupo"].tolist(), ["alto", "alto", "bajo"])
        self.assertEqual(principal.loc["2007-02", "fecha_vix_previo"], pd.Timestamp("2007-01-31"))

    def test_vix_faltante_deja_sin_clasificar_sin_asignar_grupo_bajo(self):
        self.datos.loc[pd.Timestamp("2007-02-28"), "VIX"] = np.nan
        rend = a.calcular_rendimientos_mensuales(self.datos)
        salida = a.clasificar_por_vix(self.datos, rend, 30)
        self.assertTrue(pd.isna(salida.loc["2007-03", "grupo"]))
        self.assertTrue(pd.isna(salida.loc["2007-03", "fecha_vix_previo"]))
        self.assertEqual(salida.loc["2007-04", "vix_previo"], 19)

    def test_validacion_excluye_feriado_e_infinito_pero_conserva_copia(self):
        datos = self.datos.copy()
        datos.loc[pd.Timestamp("2007-01-01")] = 100
        datos.loc[pd.Timestamp("2007-02-28"), "PUT"] = np.inf
        datos = datos.sort_index(ascending=False)
        original = datos.copy(deep=True)
        controles = a.Controles()
        salida = a.validar_datos(datos, controles)
        self.assertNotIn(pd.Timestamp("2007-01-01"), salida.index)
        self.assertTrue(pd.isna(salida.loc[pd.Timestamp("2007-02-28"), "PUT"]))
        self.assertTrue(salida.index.is_monotonic_increasing)
        self.assertTrue(any(f["tipo"] == "valor_invalido" for f in controles.incidencias))
        pd.testing.assert_frame_equal(datos, original)



class MetricasTest(unittest.TestCase):
    def test_exportacion_distingue_mes_de_fecha_real_de_cierre(self):
        tabla = pd.DataFrame(
            {"fecha_cierre": [pd.Timestamp("2007-03-30")]},
            index=pd.PeriodIndex(["2007-03"], freq="M", name="mes"),
        )
        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "salida.csv"
            for usar_indice in (True, False):
                with self.subTest(usar_indice=usar_indice):
                    a.guardar_csv(tabla if usar_indice else tabla.reset_index(), destino, indice=usar_indice)
                    with destino.open(encoding="utf-8-sig", newline="") as archivo:
                        fila = next(csv.DictReader(archivo))
                    self.assertEqual(fila["mes"], "2007-03")
                    self.assertEqual(fila["fecha_cierre"], "2007-03-30")

    def test_muestras_pareadas_grupo_vacio_y_ddof_muestral(self):
        tabla = pd.DataFrame({
            "PUT": [0.1, -0.2, 0.3], "CNDR": [np.nan] * 3,
            "PPUT": [0.01, np.nan, np.nan], "SPY": [0.05, np.nan, 0.10],
            "grupo": ["alto"] * 3,
        }, index=pd.period_range("2007-02", periods=3, freq="M"))
        resumen = a.calcular_metricas(tabla, 30).set_index(["serie", "grupo"])
        put = resumen.loc[("PUT", "alto")]
        self.assertEqual(put["cantidad_observaciones"], 3)
        self.assertAlmostEqual(put["rendimiento_medio_pct"], 20 / 3)
        self.assertAlmostEqual(put["mediana_pct"], 10)
        self.assertAlmostEqual(put["desviacion_estandar_pct"], 25.16611478423583)
        self.assertAlmostEqual(put["porcentaje_meses_negativos"], 100 / 3)
        self.assertAlmostEqual(put["peor_rendimiento_mensual_pct"], -20)
        self.assertEqual(put["cantidad_pares_vs_spy"], 2)
        self.assertAlmostEqual(put["diferencia_media_vs_spy_pp"], 12.5)
        self.assertEqual(resumen.loc[("CNDR", "alto"), "cantidad_observaciones"], 0)
        self.assertTrue(pd.isna(resumen.loc[("PPUT", "alto"), "desviacion_estandar_pct"]))
        for serie in ("PUT", "CNDR", "PPUT", "SPY"):
            vacio = resumen.loc[(serie, "bajo")]
            self.assertEqual(vacio["cantidad_observaciones"], 0)
            self.assertTrue(pd.isna(vacio["rendimiento_medio_pct"]))


if __name__ == "__main__":
    unittest.main()
