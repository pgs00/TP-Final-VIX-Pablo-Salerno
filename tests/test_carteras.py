"""Muestras artificiales para comprobar la simulación; no son datos del estudio."""

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import analisis as a


class CarterasTest(unittest.TestCase):
    def setUp(self):
        parametros = patch.multiple(
            a, FECHA_INICIO_DATOS="2007-01-01", FECHA_FIN_DATOS="2007-04-30",
            FECHA_INICIO_ANALISIS="2007-02-01", FECHA_FIN_ANALISIS="2007-04-30",
        )
        parametros.start()
        self.addCleanup(parametros.stop)
        self.tabla = pd.DataFrame({
            "SPY": [-0.10, 0.20, -0.05], "PUT": [0.10, -0.20, 0.30],
            "CNDR": [-0.02, 0.03, 0.04], "PPUT": [0.05, 0.06, 0.07],
            "vix_previo": [30.0, 25.0, 10.0],
            "fecha_vix_previo": pd.to_datetime(["2007-01-31", "2007-02-28", "2007-03-30"]),
        }, index=pd.period_range("2007-02", periods=3, freq="M", name="mes"))

    def test_siete_carteras_capitalizan_en_orden_y_mantienen_indice(self):
        original = self.tabla.copy(deep=True)
        capitales, asignaciones, resumen = a.simular_carteras(self.tabla.iloc[::-1], 30)
        self.assertEqual(capitales.index.astype(str).tolist(), ["2007-01", "2007-02", "2007-03", "2007-04"])
        self.assertTrue(capitales.iloc[0].eq(10000).all())
        np.testing.assert_allclose(capitales["SIEMPRE_SPY"], [10000, 9000, 10800, 10260])
        finales = {
            "SIEMPRE_SPY": 10260, "PUT_VIX_ALTO_30": 12540, "CNDR_VIX_ALTO_30": 11172,
            "PPUT_VIX_ALTO_30": 11970, "SIEMPRE_PUT": 11440,
            "SIEMPRE_CNDR": 10497.76, "SIEMPRE_PPUT": 11909.1,
        }
        self.assertEqual(set(capitales.columns), set(finales))
        for cartera, final in finales.items():
            self.assertAlmostEqual(capitales.iloc[-1][cartera], final)
        for serie in ("PUT", "CNDR", "PPUT"):
            altos = asignaciones.loc[asignaciones["cartera"] == f"{serie}_VIX_ALTO_30", "activo_asignado"]
            siempre = asignaciones.loc[asignaciones["cartera"] == f"SIEMPRE_{serie}", "activo_asignado"]
            self.assertEqual(altos.tolist(), [serie, "SPY", "SPY"])
            self.assertEqual(siempre.tolist(), [serie, serie, serie])
        self.assertTrue(resumen["estado"].eq("completa").all())
        self.assertTrue(resumen["meses_capitalizados"].eq(3).all())
        pd.testing.assert_frame_equal(self.tabla, original)

    def test_sensibilidad_25_incluye_igualdad(self):
        capitales, asignaciones, _ = a.simular_carteras(self.tabla, 25)
        self.assertAlmostEqual(capitales.loc["2007-04", "PUT_VIX_ALTO_25"], 8360)
        self.assertEqual(len(capitales.columns), 3)
        activos = asignaciones.loc[asignaciones["cartera"] == "PUT_VIX_ALTO_25", "activo_asignado"]
        self.assertEqual(activos.tolist(), ["PUT", "PUT", "SPY"])

    def test_maxima_caida_incluye_inicial_y_no_es_el_peor_retorno(self):
        _, _, resumen = a.simular_carteras(self.tabla, 30)
        resumen = resumen.set_index("cartera")
        self.assertAlmostEqual(resumen.loc["SIEMPRE_SPY", "maxima_caida_acumulada_cierres_mensuales_pct"], -10)
        self.tabla["SPY"] = [-0.10, -0.20, 0.30]
        _, _, otro = a.simular_carteras(self.tabla, 30)
        self.assertAlmostEqual(otro.set_index("cartera").loc["SIEMPRE_SPY", "maxima_caida_acumulada_cierres_mensuales_pct"], -28)

    def test_cagr_usa_meses_de_rendimiento_no_cantidad_de_cierres(self):
        _, _, resumen = a.simular_carteras(self.tabla, 30)
        fila = resumen.set_index("cartera").loc["SIEMPRE_SPY"]
        self.assertAlmostEqual(fila["rendimiento_anual_compuesto_pct"], 100 * (1.026 ** 4 - 1))

    def test_rendimiento_necesario_faltante_interrumpe_sin_reanudar(self):
        self.tabla.loc["2007-03", "PUT"] = np.nan
        capitales, asignaciones, resumen = a.simular_carteras(self.tabla, 30)
        self.assertEqual(capitales.loc["2007-02", "SIEMPRE_PUT"], 11000)
        self.assertTrue(capitales.loc["2007-03":, "SIEMPRE_PUT"].isna().all())
        self.assertTrue(capitales["PUT_VIX_ALTO_30"].notna().all())  # PUT no se usa en marzo.
        fila = resumen.set_index("cartera").loc["SIEMPRE_PUT"]
        self.assertEqual(fila["estado"], "incompleta")
        self.assertEqual(fila["primer_mes_incompleto"], "2007-03")
        self.assertEqual(fila["meses_capitalizados"], 1)
        for campo in ("capital_final_usd", "rendimiento_acumulado_pct", "rendimiento_anual_compuesto_pct", "maxima_caida_acumulada_cierres_mensuales_pct"):
            self.assertTrue(pd.isna(fila[campo]))
        abril = asignaciones.loc[(asignaciones["mes"] == "2007-04") & (asignaciones["cartera"] == "SIEMPRE_PUT")].iloc[0]
        self.assertEqual(abril["activo_asignado"], "PUT")
        self.assertTrue(pd.isna(abril["rendimiento_aplicado"]))
        self.assertTrue(pd.isna(abril["capital_usd"]))

    def test_senal_faltante_afecta_condicionales_pero_spy_no_la_necesita(self):
        self.tabla.loc["2007-03", "vix_previo"] = np.nan
        capitales, asignaciones, resumen = a.simular_carteras(self.tabla, 30)
        self.assertAlmostEqual(capitales.loc["2007-04", "SIEMPRE_SPY"], 10260)
        self.assertTrue(capitales.filter(like="VIX_ALTO").loc["2007-03":].isna().all().all())
        self.assertTrue(capitales.filter(like="SIEMPRE").notna().all().all())
        self.assertEqual(resumen["estado"].eq("incompleta").sum(), 3)
        faltantes = asignaciones.loc[(asignaciones["mes"] == "2007-03") & asignaciones["cartera"].str.contains("VIX_ALTO")]
        self.assertTrue(faltantes["activo_asignado"].isna().all())

    def test_mes_ausente_no_se_salta_y_se_conserva_en_salida(self):
        capitales, asignaciones, resumen = a.simular_carteras(self.tabla.drop(pd.Period("2007-03")), 30)
        self.assertTrue(capitales.loc["2007-03":].isna().all().all())
        self.assertEqual(len(asignaciones), 21)
        self.assertTrue(resumen["estado"].eq("incompleta").all())

    def test_duplicados_no_se_resuelven_silenciosamente(self):
        tabla = pd.concat([self.tabla, self.tabla.iloc[[0]]])
        with self.assertRaisesRegex(ValueError, "duplicad"):
            a.simular_carteras(tabla, 30)



if __name__ == "__main__":
    unittest.main()
