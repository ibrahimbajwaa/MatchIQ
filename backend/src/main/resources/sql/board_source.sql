SELECT s.player_id, s.stat_key, p.position, s.per90
FROM player_stat s
JOIN player p ON p.id = s.player_id
