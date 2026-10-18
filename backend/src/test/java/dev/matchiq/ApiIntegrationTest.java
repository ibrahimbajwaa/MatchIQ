package dev.matchiq;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import dev.matchiq.core.GoldenFiles;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Starts the whole application against real Postgres and Redis containers and checks it end to end: Flyway loads the
 * data, Redis holds the leaderboards, and the answers match what the Python pipeline computed (the golden files).
 * Skipped automatically when Docker is not available.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers(disabledWithoutDocker = true)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class ApiIntegrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    @ServiceConnection(name = "redis")
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    @Autowired
    TestRestTemplate rest;

    private JsonNode get(String url) {
        ResponseEntity<JsonNode> response = rest.getForEntity(url, JsonNode.class);
        assertEquals(HttpStatus.OK, response.getStatusCode(), url);
        return response.getBody();
    }

    private static List<Integer> ids(JsonNode entries) {
        return java.util.stream.StreamSupport.stream(entries.spliterator(), false)
                .map(e -> e.get("player").get("id").asInt()).collect(Collectors.toList());
    }

    @Test
    @Order(1)
    void overviewReportsTheLoadedDataAndTheModelsHeadlineNumbers() {
        JsonNode o = get("/api/overview");
        assertEquals(315, o.get("counts").get("players").asInt());
        assertEquals(20, o.get("counts").get("teams").asInt());
        assertEquals(380, o.get("counts").get("fixtures").asInt());
        assertEquals(370, o.get("counts").get("upcoming").asInt());
        assertEquals(2, o.get("nextGameweek").asInt());
        assertEquals(0.4974, o.get("headline").get("modelAccuracy").asDouble(), 1e-9);
        assertEquals(0.4171, o.get("headline").get("baselineAccuracy").asDouble(), 1e-9);
    }

    @Test
    @Order(2)
    void leaderboardsFromRedisMatchPythonsTopFifteenForEveryScope() {
        List<Map<String, String>> golden = GoldenFiles.read("leaderboards.csv");
        for (String scope : List.of("all", "Defender", "Midfielder", "Forward")) {
            List<Integer> want = golden.stream()
                    .filter(r -> r.get("stat").equals("expected_goals") && r.get("scope").equals(scope))
                    .map(r -> Integer.parseInt(r.get("playerId"))).collect(Collectors.toList());
            JsonNode page = get("/api/leaderboards/expected_goals?scope=" + scope + "&limit=15");
            assertEquals(want, ids(page.get("entries")), "expected_goals / " + scope);
            assertEquals(scope, page.get("scope").asText());
            assertEquals(1, page.get("entries").get(0).get("rank").asInt());
        }
    }

    @Test
    @Order(3)
    void scopeIsCaseInsensitiveAndOnlyReturnsThatPosition() {
        JsonNode page = get("/api/leaderboards/tackles?scope=defender&limit=20");
        assertEquals("Defender", page.get("scope").asText());
        for (JsonNode e : page.get("entries")) {
            assertEquals("Defender", e.get("player").get("position").asText());
        }
    }

    @Test
    @Order(4)
    void aPlayersProfileHasAllNineStatsWithPositionRanks() {
        int id = Integer.parseInt(GoldenFiles.read("similar.csv").get(0).get("playerId"));
        JsonNode profile = get("/api/players/" + id);
        assertEquals(9, profile.get("stats").size());
        for (JsonNode s : profile.get("stats")) {
            int rank = s.get("positionRank").asInt();
            assertTrue(rank >= 1 && rank <= s.get("positionTotal").asInt(), s.toString());
            assertTrue(s.get("percentile").asDouble() >= 0 && s.get("percentile").asDouble() <= 100);
        }
    }

    @Test
    @Order(5)
    void similarPlayersMatchPythonForEveryGoldenQuery() {
        List<Map<String, String>> golden = GoldenFiles.read("similar.csv");
        Map<String, List<Map<String, String>>> queries = golden.stream().collect(
                Collectors.groupingBy(r -> r.get("playerId") + "/" + r.get("samePosition"),
                        java.util.LinkedHashMap::new, Collectors.toList()));
        for (Map.Entry<String, List<Map<String, String>>> q : queries.entrySet()) {
            String[] parts = q.getKey().split("/");
            JsonNode got = get("/api/players/" + parts[0] + "/similar?limit=10&samePosition=" + parts[1]);
            assertEquals(10, got.size(), q.getKey());
            for (int i = 0; i < 10; i++) {
                assertEquals(Integer.parseInt(q.getValue().get(i).get("neighbourId")),
                        got.get(i).get("player").get("id").asInt(), q.getKey() + " #" + (i + 1));
                assertEquals(Double.parseDouble(q.getValue().get(i).get("similarity")),
                        got.get(i).get("similarity").asDouble(), 1e-9, q.getKey() + " #" + (i + 1));
            }
        }
    }

    @Test
    @Order(6)
    void livePredictionsAgreeWithThePrecomputedFixtureProbabilities() {
        JsonNode upcoming = get("/api/fixtures?status=UPCOMING");
        assertEquals(370, upcoming.size());
        for (int i = 0; i < 5; i++) {
            JsonNode f = upcoming.get(i);
            JsonNode p = get("/api/predict?homeId=" + f.get("home").get("id").asInt()
                    + "&awayId=" + f.get("away").get("id").asInt());
            // Fixture probabilities were rounded to 4 decimals by the exporter.
            assertEquals(f.get("pHome").asDouble(), p.get("pHome").asDouble(), 1e-4);
            assertEquals(f.get("pDraw").asDouble(), p.get("pDraw").asDouble(), 1e-4);
            assertEquals(f.get("pAway").asDouble(), p.get("pAway").asDouble(), 1e-4);
            assertEquals(1.0, p.get("pHome").asDouble() + p.get("pDraw").asDouble() + p.get("pAway").asDouble(), 1e-9);
        }
    }

    @Test
    @Order(7)
    void fixturesCanBeFilteredByGameweek() {
        assertEquals(10, get("/api/fixtures?gameweek=2").size());
        assertEquals(10, get("/api/fixtures?status=finished").size());
    }

    @Test
    @Order(8)
    void teamsAndRatingsCoverTheTwentyClubs() {
        assertEquals(20, get("/api/teams").size());
        JsonNode ratings = get("/api/teams/ratings");
        assertEquals(20, ratings.size());
        assertEquals(1, ratings.get(0).get("eloRank").asInt());
        assertTrue(ratings.get(0).get("history").size() > 50);
    }

    @Test
    @Order(9)
    void badRequestsGetProblemJsonWithTheRightStatus() {
        assertProblem("/api/players/999999", HttpStatus.NOT_FOUND);
        assertProblem("/api/leaderboards/nope", HttpStatus.NOT_FOUND);
        assertProblem("/api/leaderboards/goals_scored?scope=striker", HttpStatus.BAD_REQUEST);
        assertProblem("/api/leaderboards/goals_scored?limit=0", HttpStatus.BAD_REQUEST);
        assertProblem("/api/predict?homeId=1&awayId=1", HttpStatus.BAD_REQUEST);
        assertProblem("/api/fixtures?status=sometime", HttpStatus.BAD_REQUEST);
    }

    private void assertProblem(String url, HttpStatus expected) {
        ResponseEntity<JsonNode> r = rest.getForEntity(url, JsonNode.class);
        assertEquals(expected, r.getStatusCode(), url);
        assertTrue(String.valueOf(r.getHeaders().getContentType()).startsWith("application/problem+json"), url);
    }

    @Test
    @Order(99)
    void whenRedisDiesLeaderboardsKeepWorkingFromPostgresAndTheFallbackIsCounted() {
        List<Integer> before = ids(get("/api/leaderboards/goals_scored?limit=10").get("entries"));

        redis.stop();

        JsonNode page = get("/api/leaderboards/goals_scored?limit=10");
        assertEquals(before, ids(page.get("entries")), "Postgres must give the same leaderboard Redis did");
        // A player profile reads position ranks from the leaderboards too, so it must survive the outage as well.
        assertTrue(get("/api/players/" + before.get(0)).get("stats").get(0).get("positionRank").asInt() >= 1);

        String metrics = rest.getForObject("/actuator/prometheus", String.class);
        assertTrue(metrics.contains("matchiq_leaderboard_fallback_total"), "fallback counter missing");
        assertEquals("UP", get("/actuator/health/readiness").get("status").asText(),
                "losing Redis must not take the service out of rotation");
    }
}
