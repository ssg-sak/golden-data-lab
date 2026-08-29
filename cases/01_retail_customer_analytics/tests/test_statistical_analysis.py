import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import prepare_retail_frames  # noqa: E402
from statistical_analysis import (  # noqa: E402
    cliffs_delta,
    complete_months,
    cramers_v,
    drop_top_fraction,
    gini_coefficient,
    interpret_cliff_delta,
    kruskal_epsilon_squared,
    monthly_sales_summary,
    paired_wilcoxon,
    run_statistical_analysis,
    sensitivity_table,
    share_top_fraction,
    share_top_n,
)


def _sample_prepared():
    dates = pd.to_datetime(
        [
            "2010-01-05",
            "2010-01-06",
            "2010-11-02",
            "2011-01-05",
            "2011-01-08",
            "2011-11-03",
            "2009-12-15",
            "2011-12-02",
        ]
    )
    frame = pd.DataFrame(
        {
            "Invoice": ["A1", "A2", "A3", "B1", "B2", "B3", "D1", "D2"],
            "StockCode": ["P1", "P1", "P2", "P1", "P2", "P3", "P1", "P2"],
            "Description": ["One"] * 8,
            "Quantity": [2, 1, 4, 2, 1, 3, 1, 1],
            "InvoiceDate": dates,
            "Price": [10.0, 10.0, 5.0, 10.0, 20.0, 8.0, 10.0, 10.0],
            "Customer ID": [1, 1, 2, 1, 3, 2, 4, 1],
            "Country": [
                "United Kingdom",
                "France",
                "United Kingdom",
                "United Kingdom",
                "France",
                "United Kingdom",
                "United Kingdom",
                "France",
            ],
        }
    )
    extra = frame.iloc[[0]].copy()
    cancelled = pd.DataFrame(
        {
            "Invoice": ["CA1"],
            "StockCode": ["P1"],
            "Description": ["One"],
            "Quantity": [-2],
            "InvoiceDate": [pd.Timestamp("2010-02-01")],
            "Price": [10.0],
            "Customer ID": [1],
            "Country": ["United Kingdom"],
        }
    )
    return prepare_retail_frames(
        {"Year 2009-2010": pd.concat([frame, extra, cancelled], ignore_index=True)}
    )


class GiniAndShareTest(unittest.TestCase):
    def test_equal_values_have_zero_gini(self):
        self.assertAlmostEqual(gini_coefficient([3, 3, 3, 3]), 0.0)

    def test_single_recipient_gini(self):
        self.assertAlmostEqual(gini_coefficient([0, 0, 0, 1]), 0.75)

    def test_top_shares(self):
        values = [1, 1, 1, 7]
        self.assertAlmostEqual(share_top_n(values, 1), 0.7)
        self.assertAlmostEqual(share_top_fraction(values, 0.25), 0.7)

    def test_drop_top_fraction_removes_largest(self):
        series = pd.Series([1.0, 2.0, 3.0, 100.0], index=list("abcd"))
        trimmed = drop_top_fraction(series, 0.25)
        self.assertNotIn(100.0, set(trimmed.to_numpy()))
        self.assertEqual(len(trimmed), 3)


class EffectSizeTest(unittest.TestCase):
    def test_paired_wilcoxon_detects_shift(self):
        before = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        after = before + 8.0
        result = paired_wilcoxon(before, after)
        self.assertLess(result["p_value"], 0.05)
        self.assertGreater(result["rank_biserial"], 0.9)

    def test_cliffs_delta_labels(self):
        self.assertEqual(interpret_cliff_delta(0.05), "negligible")
        self.assertEqual(interpret_cliff_delta(0.40), "medium")
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = np.array([10.0, 11.0, 12.0, 13.0])
        self.assertGreater(cliffs_delta(x, y), 0.9)

    def test_kruskal_and_cramers(self):
        groups = [np.array([1.0, 2.0, 2.5]), np.array([8.0, 9.0, 10.0])]
        result = kruskal_epsilon_squared(groups)
        self.assertGreater(result["epsilon_squared"], 0)
        table = np.array([[30, 5], [10, 20]])
        self.assertGreater(cramers_v(table), 0.3)


class PipelineTest(unittest.TestCase):
    def test_complete_months_drop_partials(self):
        prepared = _sample_prepared()
        monthly = monthly_sales_summary(prepared.sales_analysis_df)
        complete = complete_months(monthly)
        self.assertFalse(complete["is_partial_month"].any())
        self.assertTrue(monthly["is_partial_month"].any())

    def test_run_statistical_analysis_returns_tables(self):
        prepared = _sample_prepared()
        results = run_statistical_analysis(prepared)
        self.assertEqual(len(results.hypothesis_summary), 4)
        self.assertIn("baseline", set(results.sensitivity["scenario"]))
        self.assertGreater(results.customer_concentration["n"], 0)
        sensitivity = sensitivity_table(prepared)
        self.assertEqual(len(sensitivity), 3)


if __name__ == "__main__":
    unittest.main()
