package dev.matchiq.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.matchiq.core.SimilarityIndex.Neighbor;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

class SimilarityIndexTest {

    private static SimilarityIndex realIndex() {
        return SimilarityIndex.build(GoldenFiles.players().stream()
                .map(p -> new SimilarityIndex.Vector(p.id(), p.position(), p.zscores()))
                .collect(Collectors.toList()));
    }

    @Test
    void givesTheSameNeighboursAsPythonForEightPlayersWithAndWithoutThePositionFilter() {
        SimilarityIndex index = realIndex();
        List<Map<String, String>> rows = GoldenFiles.read("similar.csv");
        assertEquals(160, rows.size());

        Map<String, List<Map<String, String>>> byQuery = rows.stream().collect(
                Collectors.groupingBy(r -> r.get("playerId") + "/" + r.get("samePosition"),
                        java.util.LinkedHashMap::new, Collectors.toList()));
        assertEquals(16, byQuery.size());
        for (Map.Entry<String, List<Map<String, String>>> q : byQuery.entrySet()) {
            int playerId = Integer.parseInt(q.getKey().split("/")[0]);
            boolean same = Boolean.parseBoolean(q.getKey().split("/")[1]);
            List<Neighbor> got = index.mostSimilar(playerId, 10, same);
            assertEquals(10, got.size(), q.getKey());
            for (int i = 0; i < 10; i++) {
                Map<String, String> want = q.getValue().get(i);
                assertEquals(Integer.parseInt(want.get("neighbourId")), got.get(i).id(),
                        "neighbour #" + (i + 1) + " of " + q.getKey());
                assertEquals(Double.parseDouble(want.get("similarity")), got.get(i).similarity(), 1e-9,
                        "similarity #" + (i + 1) + " of " + q.getKey());
            }
        }
    }

    @Test
    void resultsAreBestFirstAndNeverIncludeThePlayerThemselves() {
        SimilarityIndex index = realIndex();
        int id = GoldenFiles.players().get(0).id();
        List<Neighbor> got = index.mostSimilar(id, 25, false);
        assertEquals(25, got.size());
        for (int i = 0; i < got.size(); i++) {
            assertFalse(got.get(i).id() == id);
            if (i > 0) {
                assertTrue(got.get(i - 1).similarity() >= got.get(i).similarity());
            }
        }
    }

    @Test
    void positionFilterOnlyReturnsThatPosition() {
        SimilarityIndex index = realIndex();
        var byId = GoldenFiles.players().stream().collect(Collectors.toMap(GoldenFiles.GoldenPlayer::id, p -> p));
        var query = GoldenFiles.players().stream().filter(p -> p.position().equals("Defender")).findFirst().orElseThrow();
        for (Neighbor n : index.mostSimilar(query.id(), 20, true)) {
            assertEquals("Defender", byId.get(n.id()).position());
        }
    }

    @Test
    void askingForMoreThanExistReturnsEveryoneElse() {
        SimilarityIndex index = realIndex();
        int id = GoldenFiles.players().get(3).id();
        assertEquals(index.size() - 1, index.mostSimilar(id, 10_000, false).size());
    }

    @Test
    void sameDirectionMeansSimilarityOneRegardlessOfSize() {
        SimilarityIndex index = SimilarityIndex.build(List.of(
                new SimilarityIndex.Vector(1, "Forward", new double[] {1, 2, 3}),
                new SimilarityIndex.Vector(2, "Forward", new double[] {2, 4, 6}),
                new SimilarityIndex.Vector(3, "Forward", new double[] {-1, -2, -3})));
        List<Neighbor> got = index.mostSimilar(1, 2, false);
        assertEquals(2, got.get(0).id());
        assertEquals(1.0, got.get(0).similarity(), 1e-12);
        assertEquals(3, got.get(1).id());
        assertEquals(-1.0, got.get(1).similarity(), 1e-12);
    }

    @Test
    void equalSimilaritiesAreOrderedByPlayerIdSoResultsAreDeterministic() {
        List<SimilarityIndex.Vector> vs = new ArrayList<>();
        vs.add(new SimilarityIndex.Vector(100, "Forward", new double[] {1, 0}));
        for (int id : new int[] {7, 3, 9, 5}) {
            vs.add(new SimilarityIndex.Vector(id, "Forward", new double[] {1, 0}));
        }
        List<Neighbor> got = SimilarityIndex.build(vs).mostSimilar(100, 3, false);
        assertEquals(List.of(3, 5, 7), got.stream().map(Neighbor::id).toList());
    }

    @Test
    void aPlayerWithAnAllZeroProfileIsSimilarToNobody() {
        SimilarityIndex index = SimilarityIndex.build(List.of(
                new SimilarityIndex.Vector(1, "Midfielder", new double[] {0, 0}),
                new SimilarityIndex.Vector(2, "Midfielder", new double[] {1, 1})));
        assertEquals(0.0, index.mostSimilar(1, 1, false).get(0).similarity(), 0.0);
        assertEquals(0.0, index.mostSimilar(2, 1, false).get(0).similarity(), 0.0);
    }

    @Test
    void rejectsUnknownPlayersAndBadK() {
        SimilarityIndex index = realIndex();
        assertThrows(NoSuchElementException.class, () -> index.mostSimilar(-1, 5, false));
        assertThrows(IllegalArgumentException.class,
                () -> index.mostSimilar(GoldenFiles.players().get(0).id(), 0, false));
    }

    @Test
    void rejectsPlayersWhoseVectorsDifferInLength() {
        assertThrows(IllegalArgumentException.class, () -> SimilarityIndex.build(List.of(
                new SimilarityIndex.Vector(1, "Forward", new double[] {1, 2}),
                new SimilarityIndex.Vector(2, "Forward", new double[] {1, 2, 3}))));
    }
}
