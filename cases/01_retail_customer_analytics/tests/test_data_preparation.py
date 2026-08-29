import sys
import unittest
from pathlib import Path

import pandas as pd


CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import (  # noqa: E402
    add_invoice_key,
    count_exact_duplicate_extras,
    drop_exact_duplicate_extras,
    flag_mismatch_mask,
    prepare_retail_frames,
)


class PrepareRetailFramesTest(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "Invoice": ["100", "101", "C102", "103", "104"],
                "StockCode": ["A", "B", "C", "D", "E"],
                "Description": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
                "Quantity": [2, 1, -1, 3, 1],
                "InvoiceDate": pd.to_datetime(
                    ["2011-01-01", "2011-01-02", "2011-01-03", "2011-01-04", "2011-01-05"]
                ),
                "Price": [10.0, 5.0, 5.0, 2.0, 0.0],
                "Customer ID": [1, None, 2, 1, 3],
                "Country": ["UK", "UK", "UK", "France", "UK"],
            }
        )

    def test_purpose_specific_populations(self):
        prepared = prepare_retail_frames({"Year": self.frame})

        self.assertEqual(len(prepared.retail_df), 5)
        self.assertEqual(len(prepared.sales_analysis_df), 3)
        self.assertEqual(len(prepared.customer_analysis_df), 2)
        self.assertEqual(len(prepared.returns_df), 1)
        self.assertEqual(prepared.sales_analysis_df["Customer ID"].isna().sum(), 1)
        self.assertEqual(prepared.customer_analysis_df["Customer ID"].isna().sum(), 0)

    def test_sql_aligned_duplicate_definition(self):
        duplicated = pd.concat([self.frame, self.frame.iloc[[0]]], ignore_index=True)
        duplicated.loc[5, "Source_Sheet"] = "another sheet"

        self.assertEqual(count_exact_duplicate_extras(duplicated), 1)
        self.assertEqual(len(drop_exact_duplicate_extras(duplicated)), 5)

    def test_invoice_key_and_flag_mismatch(self):
        prepared = prepare_retail_frames({"Year": self.frame})
        keyed = add_invoice_key(prepared.retail_df)
        self.assertTrue(keyed["Invoice_Key"].str.startswith("Year|").all())
        self.assertEqual(int(flag_mismatch_mask(prepared.retail_df).sum()), 0)

    def test_missing_required_column_fails(self):
        with self.assertRaisesRegex(ValueError, "필수 컬럼 누락"):
            prepare_retail_frames({"Year": self.frame.drop(columns=["Invoice"])})


if __name__ == "__main__":
    unittest.main()
