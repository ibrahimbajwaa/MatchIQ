SELECT s.player_id, p.position, s.zscore
FROM player_stat s
JOIN player p ON p.id = s.player_id
JOIN stat_def d ON d.stat_key = s.stat_key
ORDER BY s.player_id, d.sort_order
