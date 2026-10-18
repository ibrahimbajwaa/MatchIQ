SELECT d.stat_key, d.label, d.description, s.raw_value, s.per90, s.percentile
FROM player_stat s
JOIN stat_def d ON d.stat_key = s.stat_key
WHERE s.player_id = :id
ORDER BY d.sort_order
