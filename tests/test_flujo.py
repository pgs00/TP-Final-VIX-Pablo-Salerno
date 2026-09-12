"""Verificación del contrato de salida y controles con los CSV locales reales."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import analisis as a


class FlujoTest(unittest.TestCase):
    def test_exporta_cinco_tablas_y_tres_graficos_con_identidades(self):
        self.assertTrue(hasattr(a, "main"), "Falta flujo consolidado")
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            with patch.multiple(a, CARPETA_TABLAS=raiz / "tablas", CARPETA_GRAFICOS=raiz / "graficos", CARPETA_CONTROLES=raiz / "controles"):
                self.assertEqual(a.main(), 0)
            self.assertEqual({p.name for p in (raiz / "tablas").iterdir()}, {
                "datos_mensuales.csv", "capitales_mensuales.csv", "comparacion_carteras.csv",
                "aporte_episodios.csv", "descriptivos_regimen.csv",
            })
            self.assertEqual(len(list((raiz / "graficos").glob("*.png"))), 3)
            self.assertEqual(len(list((raiz / "controles").iterdir())), 4)
            datos = pd.read_csv(raiz / "tablas/datos_mensuales.csv", index_col="mes")
            capitales = pd.read_csv(raiz / "tablas/capitales_mensuales.csv", index_col="mes")
            resumen = pd.read_csv(raiz / "tablas/comparacion_carteras.csv")
            episodios = pd.read_csv(raiz / "tablas/aporte_episodios.csv")
            self.assertEqual(len(datos), 228)
            self.assertEqual(len(capitales), 228)
            self.assertEqual(resumen["analisis"].value_counts().to_dict(), {"principal": 7, "sensibilidad": 3})
            self.assertEqual(datos["retorno_SPY"].notna().sum(), 227)
            np.testing.assert_allclose(datos["vix_previo"].iloc[1:], datos["nivel_VIX"].iloc[:-1])
            for serie in ("SPY", "PUT", "CNDR", "PPUT"):
                np.testing.assert_allclose(capitales[f"SIEMPRE_{serie}"], 10000 * datos[f"nivel_{serie}"] / datos[f"nivel_{serie}"].iloc[0], rtol=1e-12)
            for cartera, grupo in episodios.groupby("cartera"):
                self.assertEqual(grupo["cantidad_meses"].sum(), 227)
                self.assertAlmostEqual(grupo["factor_relativo"].prod(), capitales[cartera].iloc[-1] / capitales["SIEMPRE_SPY"].iloc[-1])
            datos.index = pd.PeriodIndex(datos.index, freq="M", name="mes")
            capitales.index = datos.index
            # Rechazar errores materiales en las salidas, además de aprobar el caso correcto.
            for objetivo in ("capital", "senal", "episodio", "cagr"):
                d, c, r, e = datos.copy(), capitales.copy(), resumen.copy(), episodios.copy()
                if objetivo == "capital":
                    c.loc["2008-10", "PUT_VIX_ALTO_30"] += 100
                elif objetivo == "senal":
                    d.loc["2008-10", "vix_previo"] += 1
                elif objetivo == "episodio":
                    e.loc[0, "factor_relativo"] += 0.01
                else:
                    r.loc[0, "rendimiento_anual_compuesto_pct"] += 1
                with self.subTest(objetivo=objetivo), self.assertRaises(ValueError):
                    a.verificar_resultados(d, c, r, e)
