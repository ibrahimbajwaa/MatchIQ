SELECT s.player_id AS id, s.per90 AS score
FROM player_stat s
JOIN player p ON p.id = s.player_id
WHERE s.stat_key = :stat AND (:scope = 'all' OR p.position = :scope)
ORDER BY s.per90 DESC, s.player_id DESC
LIMIT :limit OFFSET :offset
