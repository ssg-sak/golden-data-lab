import sys
import unittest
from pathlib import Path

import pandas as pd


CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import prepare_retail_frames  # noqa: E402
from kpi_segmentation import (  # noqa: E402
    action_for_segment,
    assign_rfm_segment,
    build_rfm,
    compute_kpi_values,
    run_kpi_segmentation,
)


class SegmentRuleTest(unittest.TestCase):
    def test_mutually_exclusive_priority_order(self):
        self.assertEqual(assign_rfm_segment(5, 5, 5), "Champions")
        self.assertEqual(assign_rfm_segment(1, 5, 5), "Cannot Lose")
        self.assertEqual(assign_rfm_segment(2, 4, 2), "At Risk")
        self.assertEqual(assign_rfm_segment(5, 1, 2), "New / Recent")
        self.assertEqual(assign_rfm_segment(4, 5, 2), "Loyal")
        self.assertEqual(assign_rfm_segment(3, 2, 5), "Potential")
        self.assertEqual(assign_rfm_segment(3, 2, 2), "Need Attention")
        self.assertEqual(assign_rfm_segment(1, 1, 5), "Hibernating High Value")
        self.assertEqual(assign_rfm_segment(1, 1, 1), "Hibernating")

    def test_action_mapping(self):
        self.assertEqual(action_for_segment("Champions"), "유지")
        self.assertEqual(action_for_segment("Cannot Lose"), "재활성화")
        self.assertEqual(action_for_segment("Hibernating"), "저우선")


class KpiPipelineTest(unittest.TestCase):
    def setUp(self):
        frame = pd.DataFrame(
            {
                "Invoice": ["1", "2", "3", "4", "5"],
                "StockCode": ["A", "A", "B", "B", "C"],
                "Description": ["x"] * 5,
                "Quantity": [1, 1, 2, 1, 1],
                "InvoiceDate": pd.to_datetime(
                    [
                        "2010-01-01",
                        "2010-02-01",
                        "2010-01-15",
                        "2011-06-01",
                        "2011-06-02",
                    ]
                ),
                "Price": [10.0, 10.0, 5.0, 20.0, 8.0],
                "Customer ID": [1, 1, 2, 2, 3],
                "Country": ["United Kingdom"] * 4 + ["France"],
            }
        )
        self.prepared = prepare_retail_frames({"Year": frame})

    def test_kpi_values_use_documented_denominators(self):
        values = compute_kpi_values(self.prepared).set_index("kpi")["value"]
        self.assertAlmostEqual(values["Gross sales"], 58.0)
        self.assertEqual(values["Completed orders"], 5)
        self.assertAlmostEqual(values["AOV"], 11.6)
        self.assertAlmostEqual(values["UK revenue share"], 50.0 / 58.0)

    def test_rfm_snapshot_and_repeat_customer(self):
        snapshot = pd.Timestamp("2011-06-03")
        rfm = build_rfm(self.prepared.customer_analysis_df, snapshot)
        self.assertEqual(len(rfm), 3)
        self.assertEqual(int(rfm.loc["1", "frequency"]), 2)
        self.assertEqual(int(rfm.loc["1", "recency_days"]), 487)
        results = run_kpi_segmentation(self.prepared)
        self.assertEqual(results.snapshot_date.normalize(), pd.Timestamp("2011-06-03"))
        self.assertFalse(results.segment_summary.empty)
        self.assertIn("retention", results.cohort_retention.columns)


if __name__ == "__main__":
    unittest.main()
