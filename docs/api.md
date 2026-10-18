# API reference

Base path `/api`. Everything is `GET` and returns JSON. Errors are [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807)
problem details (`application/problem+json` with `title`, `status`, `detail`). Responses carry an `ETag`, so clients
that send `If-None-Match` get `304` when nothing changed. Every response has an `X-Request-Id` header that also appears in
the server logs.

The response shapes are the records in `backend/src/main/java/dev/matchiq/api/Dtos.java`. The frontend's mock API is
checked against those records in CI (`npm run check:contract`), so this page and the code cannot quietly disagree.

| Route | Parameters | Returns |
|---|---|---|
| `/overview` | | Data dates, counts, the next gameweek, and the model's headline accuracy |
| `/stats` | | The nine statistics, with plain-English descriptions |
| `/leaderboards/{stat}` | `scope` = `all` (default), `Defender`, `Midfielder`, `Forward` (case-insensitive); `offset` (default 0); `limit` 1 to 100 (default 25) | One page of ranked players. Ranks use competition ranking, so ties read 1, 2, 2, 4 |
| `/players` | `q` (name search); `limit` 1 to 25 (default 8) | Matching players, best match first |
| `/players/{id}` | | The player and all nine stats, each with a percentile and a rank among players in the same position |
| `/players/{id}/similar` | `limit` 1 to 50 (default 10); `samePosition` (default false) | Players who play alike, with cosine similarity |
| `/scout/map` | | Every scouted player's 2-D position and playing style |
| `/teams` | `league` (default true: only current Premier League clubs) | Clubs with current Elo and rank |
| `/teams/ratings` | | Clubs with their Elo history |
| `/fixtures` | `gameweek`; `status` = `upcoming` or `finished` | Fixtures with the model's probabilities, and the result if played |
| `/predict` | `homeId`, `awayId` (different clubs) | Win, draw and loss probabilities for any pairing |
| `/model` | | Accuracy and log loss for every model tried, and per-season results |

Operations: `/actuator/health/liveness`, `/actuator/health/readiness`, `/actuator/prometheus`.

## Failure behaviour

- **Redis down:** leaderboards fall back to the same ranking computed in Postgres, `matchiq_leaderboard_fallback_total`
  counts each fallback, and readiness stays up. Redis is rebuilt from Postgres every 30 seconds and swapped in atomically
  (`RENAME`), so readers never see a half-built board.
- **Postgres down:** readiness fails, so an orchestrator stops routing traffic to the instance.
