package dev.matchiq.store;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Loads the queries in {@code src/main/resources/sql}. Keeping SQL in its own files means each query can be run in
 * psql as is, and the repositories stay free of long strings.
 */
final class Sql {

    private static final Map<String, String> CACHE = new ConcurrentHashMap<>();

    private Sql() {
    }

    static String get(String name) {
        return CACHE.computeIfAbsent(name, Sql::read);
    }

    private static String read(String name) {
        try (InputStream in = Sql.class.getResourceAsStream("/sql/" + name + ".sql")) {
            if (in == null) {
                throw new IllegalStateException("missing query file sql/" + name + ".sql");
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
