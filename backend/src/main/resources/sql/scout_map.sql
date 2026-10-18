SELECT p.id, p.name, t.short_name AS team_short, p.position, p.style, p.pca_x, p.pca_y
FROM player p
JOIN team t ON t.id = p.team_id
ORDER BY p.id
