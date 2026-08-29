# CASE 02 작업 기록

시간순 실행 기록이다. 비밀번호와 키는 적지 않는다.

## 2026-08-29 기획 확정과 원본 확보

- 행정안전부 Open API는 2022-10 이후·짧은 기간·서비스 키 필요라 이 환경에서는 쓰지 않기로 했다.
- 국가데이터처 게시판 `list_no=443278` seq=4에서 「2025년 국내인구이동통계 결과」 xlsx를 받았다. KDI 사본과 바이트가 같다.
- SHA-256 `FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D`, 204,601 bytes.
- 청년 정의는 원표 5세 구간 합 20-39로 잠갔다. e-지방지표 19-39와 대사하지 않는다.
- OD는 서울 행 대사로 행=전입지, 열=전출지로 잠갔다. 연령별 OD는 부표에 없다.

## 2026-08-29 파서·품질·후속 단계

- `src/parse_official_tables.py`로 분석 시트 10개를 tidy 표로 읽었다. 잔여 시트 `8.월별`(2009-2011)은 제외했다.
- 단위 테스트 8건 통과. 품질 검사 14/14 PASS.
- `src/run_analysis.py`가 KPI, 가설 4개, 대시보드 PNG, `evidence/analysis_summary.json`을 썼다.
- 핵심 재현 값: 총이동 6,117,784, 청년 이동자 2,761,243, 서울 20-24 순이동 +25,664, 서울 30-34 −10,861.

## 2026-08-29 PostgreSQL 적재 및 검증

### 실행 환경

| 항목 | 확인 결과 |
| --- | --- |
| Database | `golden_data_lab` |
| Schema | `migration` |
| PostgreSQL | 18.4, Windows 64-bit |
| Loader | `src/load_to_postgres.py` 1.0.0 |

### 적재 결과

- `migration.load_audit.load_id`: 1
- 시작: 2026-08-29 11:48:55 KST
- 종료: 2026-08-29 11:48:55 KST
- 원본 SHA-256: `FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D`
- 상태: `success`
- `national_movers_yearly` 56행 (1970-2025). 표 1 각주 행은 제외

첫 적재에서 각주 `* 1970년...`이 연도 1970으로 들어가 57행·`movers_total` 결측 1건이 나왔다. 파서가 각주를 건너뛰도록 고친 뒤 `--replace`로 다시 적재했다.

### 검증 결과

```text
PASS: source, audit, and PostgreSQL migration tables reconcile (2025 movers 6117784)
```

증빙 파일:

- `evidence/validation_20260829.log`: `psql -L` 로그
- `evidence/validation_20260829_full.log`: 표준 출력·오류 포함

### SQL에서 확인한 값

| 검사 | 결과 |
| --- | --- |
| 2025 총이동자 | 6,117,784 `passed` |
| 청년 20-39 이동자 | 2,761,243 `passed` |
| 서울 20-24 / 30-34 순이동 | +25,664 / −10,861 `passed` |
| OD 서울 시도간 전입 | 438,327 `passed` |
| 수도권 순이동 | +38,465 `passed` |
| 결측 | 0 `passed` |

## 한계

- 시군구 청년 순이동과 연령별 시도 간 OD는 이 부표가 아니라 KOSIS 별도 표다.
- 지도 경계는 통계청 2018 시도 폴리곤이다. 표시를 위해 울릉·독도는 잘랐다. 경북 값은 시도 전체다.

## 2026-08-29 노트북 실행

- `src/execute_notebooks.py`로 `01`–`05` 노트북을 실행하고 셀 출력을 저장했다.
- 한 페이지 PNG의 카드 숫자는 Total movers 6,117,784, 청년 이동자 2,761,243과 같다.

## 2026-08-29 Power BI 제거

시각화 7단계는 matplotlib PNG와 노트북만 남긴다. `powerbi/` 폴더, `.pbix`, `src/build_powerbi_pbix.py`를 삭제했다.

## 2026-08-29 시도 경계 지도

- `southkorea/southkorea-maps`의 통계청 2018 시도 GeoJSON을 받아 SHA-256을 잠갔다.
- 17개 시도를 KOSTAT 코드로 연결해 `data/geo/sido_boundaries.geojson`을 만들었다.
- 한 페이지 대시보드와 `evidence/figures/01_youth_net_2025.png`를 단계색지도로 바꿨다.

