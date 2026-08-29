"""Pre-specified statistical checks for CASE 02.

p-values are easy to reject with 21 years or 17 regions. Every test reports an
effect size. Results describe registered domestic moves in the official annex,
not desired migration or current policy impact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

from data_preparation import PreparedMigrationData
from parse_official_tables import OfficialTables


ALPHA = 0.05


def _wilcoxon_effect(diff: np.ndarray) -> dict[str, Any]:
    stat, p_value = wilcoxon(diff, alternative="two-sided", zero_method="wilcox")
    n = diff.size
    rank_biserial = float(stat / (n * (n + 1) / 4) * 2 - 1) if n else float("nan")
    # scipy Wilcoxon statistic is the sum of positive ranks. Convert to a signed
    # matched-pairs rank-biserial using the mean of signed differences' signs.
    n_pos = int(np.sum(diff > 0))
    n_neg = int(np.sum(diff < 0))
    if n_pos + n_neg:
        rank_biserial = (n_pos - n_neg) / (n_pos + n_neg)
    return {
        "n": int(n),
        "statistic": float(stat),
        "p_value": float(p_value),
        "median_diff": float(np.median(diff)),
        "rank_biserial": float(rank_biserial),
        "alpha": ALPHA,
        "significant": bool(p_value < ALPHA),
    }


def youth_vs_midlife_mobility(youth_mobility: pd.DataFrame) -> dict[str, Any]:
    """Paired years 2005-2025: 20-24 mobility rate vs 40-44 mobility rate."""

    left = youth_mobility["20-24"].to_numpy(dtype=float)
    right = youth_mobility["40-44"].to_numpy(dtype=float)
    result = _wilcoxon_effect(left - right)
    result["hypothesis"] = "H1"
    result["statement"] = (
        "연도별로 짝지은 20-24세 이동률이 40-44세 이동률과 같다"
    )
    result["alternative"] = "two-sided Wilcoxon signed-rank on yearly rate differences"
    result["median_20_24"] = float(np.median(left))
    result["median_40_44"] = float(np.median(right))
    return result


def youth_share_trend(youth_mobility: pd.DataFrame) -> dict[str, Any]:
    """Spearman year vs youth share of all movers, 2005-2025."""

    years = youth_mobility["year"].to_numpy(dtype=float)
    share = youth_mobility["youth_share_of_movers"].to_numpy(dtype=float)
    rho, p_value = spearmanr(years, share)
    return {
        "hypothesis": "H2",
        "statement": "2005-2025 청년(20-39) 이동자 비중이 연도와 상관없다",
        "n": int(years.size),
        "spearman_rho": float(rho),
        "p_value": float(p_value),
        "alpha": ALPHA,
        "significant": bool(p_value < ALPHA),
        "share_2005": float(share[0]),
        "share_2025": float(share[-1]),
    }


def youth_net_vs_total_net(youth_profile: pd.DataFrame) -> dict[str, Any]:
    """Spearman: 2025 sido total net vs youth 20-39 net."""

    total = youth_profile["net_total"].to_numpy(dtype=float)
    youth = youth_profile["net_youth_20_39"].to_numpy(dtype=float)
    rho, p_value = spearmanr(total, youth)
    sign_match = int(np.sum(np.sign(total) == np.sign(youth)))
    return {
        "hypothesis": "H3",
        "statement": "2025 시도 전체 순이동과 청년(20-39) 순이동이 상관없다",
        "n": int(total.size),
        "spearman_rho": float(rho),
        "p_value": float(p_value),
        "alpha": ALPHA,
        "significant": bool(p_value < ALPHA),
        "same_sign_sidos": sign_match,
        "same_sign_share": sign_match / total.size,
    }


def capital_net_regimes(capital_yearly: pd.DataFrame) -> dict[str, Any]:
    """Wilcoxon: capital net 1990-2010 vs 2011-2025 yearly series, unpaired via two-sample ranks.

    These are two historical windows of the same official series, not a policy
    experiment. Mann-Whitney is used because years are not paired.
    """

    from scipy.stats import mannwhitneyu

    early = capital_yearly.loc[
        capital_yearly["year"].between(1990, 2010), "net"
    ].to_numpy(dtype=float)
    late = capital_yearly.loc[
        capital_yearly["year"].between(2011, 2025), "net"
    ].to_numpy(dtype=float)
    stat, p_value = mannwhitneyu(early, late, alternative="two-sided")
    n1, n2 = early.size, late.size
    cliffs = (2 * stat) / (n1 * n2) - 1
    return {
        "hypothesis": "H4",
        "statement": "수도권 순이동(비수도권 대비)의 1990-2010 분포와 2011-2025 분포가 같다",
        "n_early": int(n1),
        "n_late": int(n2),
        "statistic": float(stat),
        "p_value": float(p_value),
        "cliffs_delta": float(cliffs),
        "median_early": float(np.median(early)),
        "median_late": float(np.median(late)),
        "alpha": ALPHA,
        "significant": bool(p_value < ALPHA),
        "note": "등록 이동의 역사 구간 비교이며 수도권 정책 효과의 인과 증거가 아니다",
    }


def youth_inflow_concentration(youth_profile: pd.DataFrame) -> dict[str, Any]:
    positive = youth_profile.loc[youth_profile["net_youth_20_39"] > 0, "net_youth_20_39"]
    total_positive = float(positive.sum())
    ranked = positive.sort_values(ascending=False)
    top3 = ranked.head(3)
    return {
        "positive_sido_count": int(positive.size),
        "positive_youth_net_sum": int(total_positive),
        "top3_sidos": list(top3.index),
        "top3_values": [int(value) for value in top3.tolist()],
        "top3_share_of_positive_youth_net": float(top3.sum() / total_positive)
        if total_positive
        else float("nan"),
    }


def sensitivity_youth_definition(youth_profile: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sido, row in youth_profile.set_index("sido").iterrows():
        sign_39 = np.sign(row["net_youth_20_39"])
        sign_34 = np.sign(row["net_youth_20_34"])
        rows.append(
            {
                "sido": sido,
                "net_20_39": int(row["net_youth_20_39"]),
                "net_20_34": int(row["net_youth_20_34"]),
                "sign_flips": bool(sign_39 != sign_34 and sign_39 != 0 and sign_34 != 0),
                "typology_20_39": row["typology"],
            }
        )
    return pd.DataFrame(rows)


@dataclass
class StatisticalResults:
    h1: dict[str, Any]
    h2: dict[str, Any]
    h3: dict[str, Any]
    h4: dict[str, Any]
    concentration: dict[str, Any]
    sensitivity: pd.DataFrame
    hypothesis_summary: pd.DataFrame


def run_statistical_analysis(
    tables: OfficialTables, prepared: PreparedMigrationData
) -> StatisticalResults:
    h1 = youth_vs_midlife_mobility(prepared.youth_mobility)
    h2 = youth_share_trend(prepared.youth_mobility)
    h3 = youth_net_vs_total_net(prepared.youth_profile)
    h4 = capital_net_regimes(tables.capital_yearly)
    concentration = youth_inflow_concentration(prepared.youth_profile.set_index("sido"))
    sensitivity = sensitivity_youth_definition(prepared.youth_profile)
    summary = pd.DataFrame(
        [
            {
                "hypothesis": item["hypothesis"],
                "p_value": item["p_value"],
                "significant_at_0.05": item["significant"],
                "effect": item.get("rank_biserial", item.get("spearman_rho", item.get("cliffs_delta"))),
                "statement": item["statement"],
            }
            for item in (h1, h2, h3, h4)
        ]
    )
    return StatisticalResults(
        h1=h1,
        h2=h2,
        h3=h3,
        h4=h4,
        concentration=concentration,
        sensitivity=sensitivity,
        hypothesis_summary=summary,
    )
