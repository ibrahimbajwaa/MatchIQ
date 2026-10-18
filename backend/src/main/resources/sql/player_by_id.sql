SELECT p.id, p.name, p.full_name, p.team_id, t.display_name AS team_name, t.short_name AS team_short,
       p.position, p.minutes, p.style
FROM player p
JOIN team t ON t.id = p.team_id
WHERE p.id = :id
