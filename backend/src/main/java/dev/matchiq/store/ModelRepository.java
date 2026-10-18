package dev.matchiq.store;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.matchiq.api.Dtos.Counts;
import dev.matchiq.api.Dtos.ModelMetric;
import dev.matchiq.api.Dtos.SeasonMetric;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class ModelRepository {

    /** Row counts plus the first gameweek that still has matches to play (null when the season is over). */
    public record Totals(Counts counts, Integer nextGameweek) {
    }

    private final JdbcClient jdbc;
    private final ObjectMapper json;

    public ModelRepository(JdbcClient jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    /** Facts about the dataset (data cut-off date, seasons used for training and testing, ...). */
    public Map<String, Object> meta() {
        Map<String, Object> out = new LinkedHashMap<>();
        jdbc.sql(Sql.get("meta")).query((rs, n) -> {
            try {
                out.put(rs.getString("k"), json.readValue(rs.getString("v"), Object.class));
            } catch (JsonProcessingException e) {
                throw new IllegalStateException("dataset_meta value is not valid JSON: " + rs.getString("k"), e);
            }
            return rs.getString("k");
        }).list();
        return out;
    }

    public Totals totals() {
        return jdbc.sql(Sql.get("overview_counts")).query((rs, n) -> new Totals(
                new Counts(rs.getInt("players"), rs.getInt("teams"), rs.getInt("fixtures"), rs.getInt("upcoming")),
                rs.getObject("next_gameweek", Integer.class))).single();
    }

    public List<ModelMetric> metrics() {
        return jdbc.sql(Sql.get("model_metrics"))
                .query((rs, n) -> new ModelMetric(rs.getString("model"), rs.getDouble("accuracy"),
                        rs.getDouble("log_loss"), rs.getBoolean("chosen")))
                .list();
    }

    public List<SeasonMetric> seasons() {
        return jdbc.sql(Sql.get("model_seasons"))
                .query((rs, n) -> new SeasonMetric(rs.getString("season"), rs.getInt("matches"),
                        rs.getDouble("model_accuracy"), rs.getDouble("home_accuracy")))
                .list();
    }
}
