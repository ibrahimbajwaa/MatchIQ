SELECT (SELECT count(*) FROM player)                                     AS players,
       (SELECT count(*) FROM team WHERE in_league)                       AS teams,
       (SELECT count(*) FROM fixture)                                    AS fixtures,
       (SELECT count(*) FROM fixture WHERE status = 'UPCOMING')          AS upcoming,
       (SELECT min(gameweek) FROM fixture WHERE status = 'UPCOMING')     AS next_gameweek
