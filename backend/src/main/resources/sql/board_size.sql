SELECT count(*)
FROM player_stat s
JOIN player p ON p.id = s.player_id
WHERE s.stat_key = :stat AND (:scope = 'all' OR p.position = :scope)
