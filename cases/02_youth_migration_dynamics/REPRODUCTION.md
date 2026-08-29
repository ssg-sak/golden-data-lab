# CASE 02 Reproduction

제3자가 같은 원본 해시와 같은 순서로 같은 숫자를 다시 만들기 위한 절차다. 비밀번호와 API 키는 저장하지 않는다.

## Source

- 파일: `cases/02_youth_migration_dynamics/data/raw/2025_domestic_migration_statistics.xlsx`
- SHA-256: `FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D`
- 크기: 204,601 bytes
- 내려받기:

```powershell
python cases/02_youth_migration_dynamics/src/download_data.py
```

공식 URL이 막히면 스크립트가 KDI 사본으로 재시도하고, 해시가 다르면 실패한다. 같은 명령이 시도 경계 GeoJSON도 받아 `data/geo/sido_boundaries.geojson`을 만든다.

시도 경계만 다시 받을 때:

```powershell
python cases/02_youth_migration_dynamics/src/download_sido_geojson.py
```

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Python path (required)

```powershell
python -m unittest discover -s cases/02_youth_migration_dynamics/tests -v
python cases/02_youth_migration_dynamics/src/run_analysis.py
python cases/02_youth_migration_dynamics/src/build_notebooks.py
python cases/02_youth_migration_dynamics/src/execute_notebooks.py
```

기대 결과:

- 단위 테스트 8건 OK
- 품질 검사 14/14 passed
- `evidence/analysis_summary.json`
- `evidence/dashboard/01_one_page_decision.png`
- `evidence/figures/01_youth_net_2025.png` (시도 단계색지도)
- 실행된 `notebooks/01`–`05`

핵심 재현 값:

| 항목 | 값 |
| --- | --- |
| 2025 총이동자 | 6,117,784 |
| 청년 이동자 20-39 | 2,761,243 |
| 서울 20-24 순이동 | +25,664 |
| 서울 30-34 순이동 | −10,861 |
| 서울←경기 이동(전 연령) | 235,668 |
| 경기←서울 이동(전 연령) | 276,867 |

노트북은 `src/execute_notebooks.py`로 셀 출력을 저장한다. 분석 숫자의 기준 산출물은 `run_analysis.py`다. 한 페이지 화면은 `src/decision_dashboard.py`가 PNG로 만든다.

## PostgreSQL path (required for SQL Extraction)

데이터베이스 `golden_data_lab`이 CASE 01에서 이미 있으면 생성 문장은 건너뛴다.

```powershell
python cases/02_youth_migration_dynamics/src/load_to_postgres.py --host localhost --port 5432 --database golden_data_lab --user postgres
python cases/02_youth_migration_dynamics/src/run_sql_validation.py
```

재적재만 `--replace`를 사용한다. 기대 메시지:

```text
PASS: source, audit, and PostgreSQL migration tables reconcile (2025 movers 6117784)
```

확인된 로그: `evidence/validation_20260829.log`, `evidence/validation_20260829_full.log`.

## What not to change

- 원본 xlsx를 편집하지 않는다.
- 청년을 19-39로 바꿔 결과를 덮어쓰지 않는다. 비교는 민감도 표로만 한다.
- 잔여 시트 `8.월별`을 월별 분석에 넣지 않는다.
- OD를 청년 경로라고 쓰지 않는다.
- 지도 경계를 2025년 지적 경계라고 쓰지 않는다. 통계청 2018 시도 폴리곤이다.
