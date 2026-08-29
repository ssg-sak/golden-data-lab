-- CASE 02 analysis views. Read-only. Youth = 20-24 + 25-29 + 30-34 + 35-39.

CREATE OR REPLACE VIEW migration.v_youth_net_2025 AS
SELECT sido,
       is_capital,
       sum(net) FILTER (WHERE age_group IN ('20-24', '25-29')) AS net_20s,
       sum(net) FILTER (WHERE age_group IN ('30-34', '35-39')) AS net_30s,
       sum(net) FILTER (
           WHERE age_group IN ('20-24', '25-29', '30-34', '35-39')
       ) AS net_youth_20_39,
       sum(net) FILTER (WHERE age_group = 'total') AS net_total
FROM migration.sido_age_net_2025
WHERE gender = 'all'
GROUP BY sido, is_capital;

CREATE OR REPLACE VIEW migration.v_inter_sido_od_2025 AS
SELECT origin,
       destination,
       movers,
       origin IN ('서울', '인천', '경기') AS origin_capital,
       destination IN ('서울', '인천', '경기') AS destination_capital
FROM migration.od_movers_2025
WHERE gender = 'all'
  AND origin NOT IN ('전국')
  AND destination NOT IN ('전국')
  AND origin <> destination;

COMMENT ON VIEW migration.v_youth_net_2025 IS
    '2025 남녀전체, 청년 20-39 순이동. 전입지×전출지 청년 OD는 원본에 없다.';
