"""Locked definitions for CASE 02. Do not infer youth origin-destination from this file."""

from __future__ import annotations

EXPECTED_SHA256 = "FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D"
EXPECTED_SIZE_BYTES = 204_601
SNAPSHOT_YEAR = 2025
LOADER_VERSION = "1.0.0"

PRIMARY_DOWNLOAD_URL = (
    "https://mods.go.kr/boardDownload.es?bid=205&list_no=443278&seq=4"
)
FALLBACK_DOWNLOAD_URL = (
    "https://eiec.kdi.re.kr/policy/callDownload.do?num=276443&filenum=2"
)
SOURCE_PAGE = "https://mods.go.kr/board.es?bid=205&mid=a10301020400&act=view&list_no=443278"
SOURCE_TITLE = "2025년 국내인구이동통계 결과"
SOURCE_PUBLISHER = "국가데이터처"

RAW_FILE_NAME = "2025_domestic_migration_statistics.xlsx"

REQUIRED_SHEETS = (
    "표지",
    "1. 성별 이동자수 및 이동률 추이",
    "2. 성 및 연령별 이동자수 및 이동률추이",
    "3. 시도별이동자추이",
    "4. 시도및성별",
    "5. 시도 및 연령별 순이동",
    "6.전입출지별(이동자)",
    "7.전입출지별(순이동)",
    "8.수도권 인구이동 추이",
    "9.월별",
    "10. 시도 및 전입사유별",
    "(참고)전입신고건수",
)
STALE_SHEET = "8.월별"

SIDOS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
)

CAPITAL_SIDOS = frozenset({"서울", "인천", "경기"})

GENDER_MAP = {
    "남녀전체": "all",
    "남자": "male",
    "여자": "female",
}

YOUTH_AGES = ("20-24", "25-29", "30-34", "35-39")
YOUTH_20S = ("20-24", "25-29")
YOUTH_30S = ("30-34", "35-39")
YOUTH_20_34 = ("20-24", "25-29", "30-34")

AGE_LABEL_MAP = {
    "계": "total",
    "0-4": "0-4",
    "5-9": "5-9",
    "10-14": "10-14",
    "15-19": "15-19",
    "20-24": "20-24",
    "25-29": "25-29",
    "30-34": "30-34",
    "35-39": "35-39",
    "40-44": "40-44",
    "45-49": "45-49",
    "50-54": "50-54",
    "55-59": "55-59",
    "60-64": "60-64",
    "65-69": "65-69",
    "70-74": "70-74",
    "75-79": "75-79",
    "80+": "80+",
}

# Official 2025 press headline used only as a reconciliation target.
HEADLINE_TOTAL_MOVERS_2025 = 6_117_784
HEADLINE_YOY_PCT_2025 = -2.6
