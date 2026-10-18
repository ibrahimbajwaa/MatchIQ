package dev.matchiq.service;

import dev.matchiq.api.BadRequestException;
import dev.matchiq.core.BoardKey;
import java.util.Map;

/** The scopes a leaderboard can be ranked within. */
final class Scopes {

    private static final Map<String, String> BY_LOWER_CASE = Map.of(
            "all", BoardKey.ALL, "defender", "Defender", "midfielder", "Midfielder", "forward", "Forward");

    private Scopes() {
    }

    /** Accepts "all", "defender", "Midfielder", ... in any case and returns the stored spelling. */
    static String normalize(String scope) {
        String canonical = scope == null ? null : BY_LOWER_CASE.get(scope.toLowerCase());
        if (canonical == null) {
            throw new BadRequestException("Unknown scope '" + scope + "'. Use all, Defender, Midfielder or Forward.");
        }
        return canonical;
    }
}
