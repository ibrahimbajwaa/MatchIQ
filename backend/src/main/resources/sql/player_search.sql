SELECT p.id, p.name, p.full_name, p.team_id, t.display_name AS team_name, t.short_name AS team_short,
       p.position, p.minutes, p.style
FROM player p
JOIN team t ON t.id = p.team_id
WHERE lower(p.name) LIKE :contains OR lower(p.full_name) LIKE :contains
ORDER BY (lower(p.name) LIKE :prefix) DESC, p.minutes DESC, p.id
LIMIT :limit
