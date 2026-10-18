package dev.matchiq.core;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Reads the CSV files in {@code src/test/resources/golden}, which {@code pipeline/src/export.py} writes from the
 * Python code. They hold what Python computed, so tests can check that Java gives the same answers.
 */
public final class GoldenFiles {

    private GoldenFiles() {
    }

    /** Rows of a golden CSV as column name to text. */
    public static List<Map<String, String>> read(String name) {
        try (InputStream in = GoldenFiles.class.getResourceAsStream("/golden/" + name)) {
            if (in == null) {
                throw new IllegalStateException("missing golden file " + name + "; run pipeline/src/export.py");
            }
            BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            String[] header = r.readLine().split(",");
            List<Map<String, String>> rows = new ArrayList<>();
            for (String line = r.readLine(); line != null; line = r.readLine()) {
                if (line.isBlank()) {
                    continue;
                }
                String[] cells = line.split(",");
                Map<String, String> row = new LinkedHashMap<>();
                for (int i = 0; i < header.length; i++) {
                    row.put(header[i], cells[i]);
                }
                rows.add(row);
            }
            return rows;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public static final List<String> STATS = List.of("goals_scored", "expected_goals", "assists", "expected_assists", "threat",
            "creativity", "tackles", "clearances_blocks_interceptions", "recoveries");

    public record GoldenPlayer(int id, String position, double[] per90, double[] zscores) {
    }

    public static List<GoldenPlayer> players() {
        List<GoldenPlayer> out = new ArrayList<>();
        for (Map<String, String> row : read("players.csv")) {
            double[] p90 = new double[STATS.size()];
            double[] z = new double[STATS.size()];
            for (int i = 0; i < STATS.size(); i++) {
                p90[i] = Double.parseDouble(row.get("p90_" + STATS.get(i)));
                z[i] = Double.parseDouble(row.get("z_" + STATS.get(i)));
            }
            out.add(new GoldenPlayer(Integer.parseInt(row.get("id")), row.get("position"), p90, z));
        }
        return out;
    }
}
