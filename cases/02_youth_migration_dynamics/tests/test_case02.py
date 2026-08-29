import sys
import unittest
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from constants import HEADLINE_TOTAL_MOVERS_2025, SIDOS  # noqa: E402
from data_preparation import assign_youth_typology, prepare_migration_data  # noqa: E402
from data_quality import run_quality_checks  # noqa: E402
from parse_official_tables import load_official_tables, parse_number  # noqa: E402


RAW = CASE_DIR / "data" / "raw" / "2025_domestic_migration_statistics.xlsx"


class ParseHelpersTest(unittest.TestCase):
    def test_spaced_thousands(self):
        self.assertEqual(parse_number("4 046 536"), 4046536.0)

    def test_typology_order(self):
        self.assertEqual(assign_youth_typology(1, 1), "Dual Magnet")
        self.assertEqual(assign_youth_typology(1, 0), "Early Career Magnet")
        self.assertEqual(assign_youth_typology(1, -1), "Early Career Magnet")
        self.assertEqual(assign_youth_typology(0, 1), "Family Settle")
        self.assertEqual(assign_youth_typology(-1, 1), "Family Settle")
        self.assertEqual(assign_youth_typology(-1, -1), "Youth Outflow")
        self.assertEqual(assign_youth_typology(0, 0), "Youth Outflow")


@unittest.skipUnless(RAW.is_file(), "official annex not downloaded")
class OfficialAnnexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = load_official_tables(RAW)
        cls.prepared = prepare_migration_data(cls.tables)

    def test_national_years_are_complete_and_unique(self):
        years = self.tables.national_movers["year"].tolist()
        self.assertEqual(years, list(range(1970, 2026)))
        self.assertFalse(self.tables.national_movers["movers_total"].isna().any())
        movers = self.tables.national_movers.set_index("year").loc[2025, "movers_total"]
        self.assertEqual(int(movers), HEADLINE_TOTAL_MOVERS_2025)

    def test_seoul_age_net_cells(self):
        net = self.tables.sido_age_net_2025
        self.assertEqual(
            int(net.query("gender=='all' and sido=='서울' and age_group=='20-24'")["net"].item()),
            25664,
        )
        self.assertEqual(
            int(net.query("gender=='all' and sido=='서울' and age_group=='30-34'")["net"].item()),
            -10861,
        )

    def test_od_orientation(self):
        od = self.tables.od_movers_2025
        seoul_from_gg = int(
            od.query("gender=='all' and destination=='서울' and origin=='경기'")["movers"].item()
        )
        gg_from_seoul = int(
            od.query("gender=='all' and destination=='경기' and origin=='서울'")["movers"].item()
        )
        self.assertEqual(seoul_from_gg, 235668)
        self.assertEqual(gg_from_seoul, 276867)
        net = int(
            self.tables.od_net_2025.query(
                "gender=='all' and destination=='서울' and origin=='경기'"
            )["net"].item()
        )
        self.assertEqual(net, seoul_from_gg - gg_from_seoul)

    def test_quality_all_pass(self):
        quality = run_quality_checks(self.tables, self.prepared)
        failed = quality.loc[~quality["passed"], "check_name"].tolist()
        self.assertEqual(failed, [])

    def test_youth_profile_covers_sidos(self):
        self.assertEqual(set(self.prepared.youth_profile["sido"]), set(SIDOS))
        seoul = self.prepared.youth_profile.set_index("sido").loc["서울"]
        self.assertEqual(seoul["typology"], "Early Career Magnet")
        self.assertEqual(int(seoul["net_20s"]), 25664 + 10273)
        self.assertEqual(int(seoul["net_30s"]), -10861 + -7869)

    def test_stale_sheet_is_flagged_not_parsed_as_monthly(self):
        self.assertTrue(self.tables.workbook["has_stale_monthly_sheet"])
        years = set(self.tables.monthly["year"])
        self.assertEqual(years, {2023, 2024, 2025})

    def test_sido_map_joins_all_regions(self):
        from sido_map import join_youth_net

        joined = join_youth_net(self.prepared.youth_profile)
        self.assertEqual(set(joined["sido"]), set(SIDOS))
        self.assertFalse(joined["net_youth_20_39"].isna().any())
        seoul = joined.set_index("sido").loc["서울"]
        self.assertEqual(int(seoul["net_youth_20_39"]), 17207)


GEO = CASE_DIR / "data" / "geo" / "sido_boundaries.geojson"


@unittest.skipUnless(GEO.is_file(), "prepared sido geojson missing")
class SidoBoundaryTest(unittest.TestCase):
    def test_seventeen_polygons(self):
        import geopandas as gpd

        frame = gpd.read_file(GEO)
        self.assertEqual(len(frame), 17)
        self.assertEqual(set(frame["sido"]), set(SIDOS))
        self.assertFalse(frame.geometry.is_empty.any())


if __name__ == "__main__":
    unittest.main()
