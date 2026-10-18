package dev.matchiq.store;

import dev.matchiq.api.Dtos.EloPoint;
import dev.matchiq.api.Dtos.Team;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class TeamRepository {

    private final JdbcClient jdbc;

    public TeamRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    private static Team team(ResultSet rs) throws SQLException {
        return new Team(rs.getInt("id"), rs.getString("name"), rs.getString("display_name"),
                rs.getString("short_name"), rs.getDouble("elo"), rs.getObject("elo_rank", Integer.class),
                rs.getBoolean("in_league"));
    }

    /** Teams in this season's league first, strongest first; clubs that only appear in last season's stats follow. */
    public List<Team> all() {
        return jdbc.sql(Sql.get("teams")).query((rs, n) -> team(rs)).list();
    }

    public Optional<Team> find(int id) {
        return jdbc.sql(Sql.get("team_by_id")).param("id", id).query((rs, n) -> team(rs)).optional();
    }

    /** Elo rating going into each match, oldest first, for every team. */
    public Map<Integer, List<EloPoint>> eloHistory() {
        record Row(int teamId, EloPoint point) {
        }
        Map<Integer, List<EloPoint>> out = new LinkedHashMap<>();
        jdbc.sql(Sql.get("elo_history"))
                .query((rs, n) -> new Row(rs.getInt("team_id"),
                        new EloPoint(rs.getObject("match_date", LocalDate.class), rs.getDouble("elo"))))
                .list()
                .forEach(r -> out.computeIfAbsent(r.teamId(), id -> new ArrayList<>()).add(r.point()));
        return out;
    }
}
