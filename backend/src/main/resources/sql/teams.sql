SELECT id, name, display_name, short_name, elo, elo_rank, in_league
FROM team
ORDER BY in_league DESC, elo DESC, id
