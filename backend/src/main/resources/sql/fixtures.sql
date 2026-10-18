SELECT f.id, f.gameweek, f.kickoff, f.status, f.home_goals, f.away_goals,
       f.p_home, f.p_draw, f.p_away, f.predicted, f.result,
       h.id AS home_id, h.short_name AS home_short, h.display_name AS home_name,
       a.id AS away_id, a.short_name AS away_short, a.display_name AS away_name
FROM fixture f
JOIN team h ON h.id = f.home_team_id
JOIN team a ON a.id = f.away_team_id
