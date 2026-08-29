"""Join 2025 youth net to sido polygons. Geometry is display-only."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from constants import PREPARED_GEOJSON_FILE_NAME, SIDOS
from shapely.geometry import box

CASE_DIR = Path(__file__).resolve().parents[1]
PREPARED_GEOJSON = CASE_DIR / "data" / "geo" / PREPARED_GEOJSON_FILE_NAME
DISPLAY_CLIP = box(124.5, 33.05, 129.65, 38.72)


def load_sido_boundaries(path: Path | None = None) -> gpd.GeoDataFrame:
    geo_path = path or PREPARED_GEOJSON
    if not geo_path.is_file():
        raise FileNotFoundError(
            f"{geo_path}가 없다. python cases/02_youth_migration_dynamics/src/download_sido_geojson.py 를 실행하세요."
        )
    frame = gpd.read_file(geo_path)
    if set(frame["sido"]) != set(SIDOS):
        raise ValueError(f"Boundary sidos {sorted(frame['sido'])} != locked SIDOS")
    return frame.to_crs(5179)


def join_youth_net(youth_profile: pd.DataFrame, boundaries: gpd.GeoDataFrame | None = None) -> gpd.GeoDataFrame:
    geo = boundaries if boundaries is not None else load_sido_boundaries()
    cols = [
        "sido",
        "net_youth_20_39",
        "net_20s",
        "net_30s",
        "net_total",
        "typology",
        "typology_ko",
    ]
    joined = geo.merge(youth_profile[cols], on="sido", how="left", validate="one_to_one")
    if joined["net_youth_20_39"].isna().any():
        missing = joined.loc[joined["net_youth_20_39"].isna(), "sido"].tolist()
        raise ValueError(f"No youth net for {missing}")
    return joined


def plot_youth_net_map(ax, youth_profile: pd.DataFrame) -> None:
    joined = join_youth_net(youth_profile)
    vmax = float(joined["net_youth_20_39"].abs().max())
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    joined.plot(
        column="net_youth_20_39",
        cmap="RdBu",
        norm=norm,
        ax=ax,
        edgecolor="#333333",
        linewidth=0.4,
        legend=True,
        legend_kwds={"label": "청년(20-39) 순이동 (명)", "shrink": 0.72},
    )
    clip = gpd.GeoSeries([DISPLAY_CLIP], crs=4326).to_crs(joined.crs).total_bounds
    ax.set_xlim(clip[0], clip[2])
    ax.set_ylim(clip[1], clip[3])
    for row in joined.itertuples(index=False):
        point = row.geometry.centroid
        if not (clip[0] <= point.x <= clip[2] and clip[1] <= point.y <= clip[3]):
            continue
        ax.annotate(
            row.sido,
            (point.x, point.y),
            ha="center",
            va="center",
            fontsize=7,
            color="#111111",
        )
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_title("2025 청년(20-39세) 시도 순이동", loc="left", weight="bold")
