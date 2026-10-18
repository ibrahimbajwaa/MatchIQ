package dev.matchiq.store;

import dev.matchiq.api.Dtos.MapPoint;
import dev.matchiq.api.Dtos.PlayerSummary;
import dev.matchiq.api.Dtos.StatDef;
import dev.matchiq.core.BoardKey;
import dev.matchiq.core.SimilarityIndex;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class PlayerRepository {

    /** One stat for one player, as stored. */
    public record StatRow(String key, String label, String description, double raw, double per90, double percentile) {
    }

    /** A player with their value for one particular stat. */
    public record PlayerStat(PlayerSummary player, double per90, double raw) {
    }

    private final JdbcClient jdbc;

    public PlayerRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    static PlayerSummary summary(ResultSet rs) throws SQLException {
        return new PlayerSummary(rs.getInt("id"), rs.getString("name"), rs.getString("full_name"),
                rs.getInt("team_id"), rs.getString("team_name"), rs.getString("team_short"),
                rs.getString("position"), rs.getInt("minutes"), rs.getString("style"));
    }

    /** Players whose short or full name contains the text, names starting with it first, then by minutes played. */
    public List<PlayerSummary> search(String text, int limit) {
        String escaped = text.toLowerCase().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
        return jdbc.sql(Sql.get("player_search"))
                .param("contains", "%" + escaped + "%")
                .param("prefix", escaped + "%")
                .param("limit", limit)
                .query((rs, n) -> summary(rs))
                .list();
    }

    public Optional<PlayerSummary> find(int id) {
        return jdbc.sql(Sql.get("player_by_id")).param("id", id).query((rs, n) -> summary(rs)).optional();
    }

    public Map<Integer, PlayerSummary> findAll(Collection<Integer> ids) {
        if (ids.isEmpty()) {
            return Map.of();
        }
        Map<Integer, PlayerSummary> out = new HashMap<>();
        jdbc.sql(Sql.get("players_by_ids")).param("ids", ids).query((rs, n) -> summary(rs)).list()
                .forEach(p -> out.put(p.id(), p));
        return out;
    }

    /** The given players with their value for one stat. */
    public Map<Integer, PlayerStat> findWithStat(String statKey, Collection<Integer> ids) {
        if (ids.isEmpty()) {
            return Map.of();
        }
        Map<Integer, PlayerStat> out = new HashMap<>();
        jdbc.sql(Sql.get("players_with_stat")).param("stat", statKey).param("ids", ids)
                .query((rs, n) -> new PlayerStat(summary(rs), rs.getDouble("per90"), rs.getDouble("raw_value")))
                .list().forEach(s -> out.put(s.player().id(), s));
        return out;
    }

    public List<StatRow> stats(int playerId) {
        return jdbc.sql(Sql.get("player_stats")).param("id", playerId)
                .query((rs, n) -> new StatRow(rs.getString("stat_key"), rs.getString("label"),
                        rs.getString("description"), rs.getDouble("raw_value"), rs.getDouble("per90"),
                        rs.getDouble("percentile")))
                .list();
    }

    public List<StatDef> statDefs() {
        return jdbc.sql(Sql.get("stat_defs"))
                .query((rs, n) -> new StatDef(rs.getString("stat_key"), rs.getString("label"),
                        rs.getString("description")))
                .list();
    }

    public List<MapPoint> scoutMap() {
        return jdbc.sql(Sql.get("scout_map"))
                .query((rs, n) -> new MapPoint(rs.getInt("id"), rs.getString("name"), rs.getString("team_short"),
                        rs.getString("position"), rs.getString("style"), rs.getDouble("pca_x"),
                        rs.getDouble("pca_y")))
                .list();
    }

    /** Every player's standardised stats, in the order of the stat definitions. */
    public List<SimilarityIndex.Vector> similarityVectors() {
        record Cell(int playerId, String position, double z) {
        }
        List<Cell> cells = jdbc.sql(Sql.get("similarity_vectors"))
                .query((rs, n) -> new Cell(rs.getInt("player_id"), rs.getString("position"), rs.getDouble("zscore")))
                .list();
        Map<Integer, List<Double>> zs = new LinkedHashMap<>();
        Map<Integer, String> positions = new HashMap<>();
        for (Cell c : cells) {
            zs.computeIfAbsent(c.playerId(), id -> new ArrayList<>()).add(c.z());
            positions.put(c.playerId(), c.position());
        }
        List<SimilarityIndex.Vector> out = new ArrayList<>(zs.size());
        zs.forEach((id, values) -> out.add(new SimilarityIndex.Vector(id, positions.get(id),
                values.stream().mapToDouble(Double::doubleValue).toArray())));
        return out;
    }

    /** Every (stat, scope) board's contents, built from the stored per-90 values. */
    public Map<BoardKey, Map<Integer, Double>> allBoards() {
        Map<BoardKey, Map<Integer, Double>> boards = new HashMap<>();
        jdbc.sql(Sql.get("board_source")).query((rs, n) -> {
            int id = rs.getInt("player_id");
            String stat = rs.getString("stat_key");
            double per90 = rs.getDouble("per90");
            boards.computeIfAbsent(BoardKey.all(stat), k -> new HashMap<>()).put(id, per90);
            boards.computeIfAbsent(new BoardKey(stat, rs.getString("position")), k -> new HashMap<>()).put(id, per90);
            return id;
        }).list();
        return boards;
    }
}
