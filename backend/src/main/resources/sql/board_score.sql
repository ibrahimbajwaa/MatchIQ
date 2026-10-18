SELECT s.per90
FROM player_stat s
JOIN player p ON p.id = s.player_id
WHERE s.stat_key = :stat AND (:scope = 'all' OR p.position = :scope) AND s.player_id = :id
