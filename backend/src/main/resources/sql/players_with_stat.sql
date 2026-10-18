SELECT p.id, p.name, p.full_name, p.team_id, t.display_name AS team_name, t.short_name AS team_short,
       p.position, p.minutes, p.style, s.per90, s.raw_value
FROM player p
JOIN team t ON t.id = p.team_id
JOIN player_stat s ON s.player_id = p.id AND s.stat_key = :stat
WHERE p.id IN (:ids)
