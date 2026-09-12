"""Casos artificiales: detectan suma de porcentajes, meses perdidos y NaN omitidos."""
import unittest

import numpy as np
import pandas as pd

import analisis as a


class EpisodiosTest(unittest.TestCase):
    def setUp(self):
        # Dos meses de restos separados por crisis. Factores relativos 1.1 y 0.9.
        self.meses = pd.PeriodIndex(["2007-02", "2008-01", "2009-12", "2020-01", "2022-12", "2025-12"], freq="M", name="mes")
        self.rendimientos = pd.DataFrame({"SPY": [0.0] * 6}, index=self.meses)
        self.asignaciones = pd.DataFrame({
            "mes": self.meses.astype(str), "cartera": "PUT_VIX_ALTO_30",
            "umbral_vix": 30, "indice_asignado": "PUT",
            "activo_asignado": ["PUT"] * 6,
            "rendimiento_aplicado": [0.10, 0, 0, 0, 0, -0.10],
        })

    def test_factores_multiplican_y_restos_no_se_tratan_como_periodo_continuo(self):
        self.assertTrue(hasattr(a, "calcular_aporte_episodios"), "Falta atribución multiplicativa")
        salida = a.calcular_aporte_episodios(self.asignaciones, self.rendimientos)
        self.assertEqual(len(salida), 4)
        resto = salida.set_index("episodio").loc["meses_restantes"]
        self.assertEqual(resto["cantidad_meses"], 2)
        self.assertAlmostEqual(resto["ventaja_relativa_pct"], -1)
        self.assertAlmostEqual(salida["factor_relativo"].prod(), 0.99)
        self.assertFalse(any("caida" in c for c in salida.columns))
        self.assertEqual(salida["cantidad_meses"].sum(), 6)

    def test_un_faltante_no_se_omite_del_producto(self):
        self.assertTrue(hasattr(a, "calcular_aporte_episodios"), "Falta atribución multiplicativa")
        self.asignaciones.loc[0, "rendimiento_aplicado"] = np.nan
        salida = a.calcular_aporte_episodios(self.asignaciones, self.rendimientos).set_index("episodio")
        self.assertEqual(salida.loc["meses_restantes", "estado"], "incompleta")
        self.assertTrue(pd.isna(salida.loc["meses_restantes", "factor_relativo"]))
