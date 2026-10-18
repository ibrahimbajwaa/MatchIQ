package dev.matchiq.store;

import dev.matchiq.api.Dtos.FixtureView;
import dev.matchiq.api.Dtos.TeamRef;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class FixtureRepository {

    private final JdbcClient jdbc;

    public FixtureRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Fixtures in kickoff order, optionally for one gameweek and/or one status (UPCOMING or FINISHED). */
    public List<FixtureView> find(Integer gameweek, String status) {
        // Only fixed fragments are appended; the values themselves are bound as parameters.
        StringBuilder sql = new StringBuilder(Sql.get("fixtures")).append(" WHERE 1 = 1");
        if (gameweek != null) {
            sql.append(" AND f.gameweek = :gameweek");
        }
        if (status != null) {
            sql.append(" AND f.status = :status");
        }
        sql.append(" ORDER BY f.kickoff, f.id");
        JdbcClient.StatementSpec spec = jdbc.sql(sql.toString());
        if (gameweek != null) {
            spec = spec.param("gameweek", gameweek);
        }
        if (status != null) {
            spec = spec.param("status", status);
        }
        return spec.query((rs, n) -> new FixtureView(
                rs.getInt("id"), rs.getInt("gameweek"), rs.getObject("kickoff", OffsetDateTime.class),
                rs.getString("status"), rs.getObject("home_goals", Integer.class),
                rs.getObject("away_goals", Integer.class),
                new TeamRef(rs.getInt("home_id"), rs.getString("home_short"), rs.getString("home_name")),
                new TeamRef(rs.getInt("away_id"), rs.getString("away_short"), rs.getString("away_name")),
                rs.getDouble("p_home"), rs.getDouble("p_draw"), rs.getDouble("p_away"),
                rs.getString("predicted"), rs.getString("result"))).list();
    }
}
