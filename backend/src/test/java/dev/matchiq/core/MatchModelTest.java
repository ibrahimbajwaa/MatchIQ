package dev.matchiq.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MatchModelTest {

    private static MatchModel model() {
        try (InputStream in = MatchModelTest.class.getResourceAsStream("/model/elo_logit.properties")) {
            return MatchModel.load(in);
        } catch (java.io.IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    @Test
    void matchesScikitLearnOnEveryGoldenCase() {
        MatchModel m = model();
        List<Map<String, String>> cases = GoldenFiles.read("predictions.csv");
        assertTrue(cases.size() >= 15, "expected the golden file to hold real and extreme cases");
        for (Map<String, String> c : cases) {
            Probabilities p = m.predict(Double.parseDouble(c.get("homeElo")), Double.parseDouble(c.get("awayElo")));
            assertEquals(Double.parseDouble(c.get("pHome")), p.home(), 1e-9, "home for " + c);
            assertEquals(Double.parseDouble(c.get("pDraw")), p.draw(), 1e-9, "draw for " + c);
            assertEquals(Double.parseDouble(c.get("pAway")), p.away(), 1e-9, "away for " + c);
        }
    }

    @Test
    void probabilitiesSumToOne() {
        MatchModel m = model();
        for (double gap = -900; gap <= 900; gap += 37.5) {
            Probabilities p = m.predict(1500 + gap, 1500);
            assertEquals(1.0, p.home() + p.draw() + p.away(), 1e-12, "gap " + gap);
        }
    }

    @Test
    void strongerSideIsFavouredAndTheGapMovesTheOdds() {
        MatchModel m = model();
        Probabilities even = m.predict(1500, 1500);
        Probabilities homeStronger = m.predict(1700, 1500);
        Probabilities awayStronger = m.predict(1500, 1700);
        assertTrue(homeStronger.home() > even.home());
        assertTrue(awayStronger.away() > even.away());
        assertTrue(even.home() > even.away(), "home advantage should show up between equal teams");
        assertEquals(Outcome.HOME_WIN, homeStronger.predicted());
        assertEquals(Outcome.AWAY_WIN, awayStronger.predicted());
    }

    @Test
    void extremeGapsStayFiniteInsteadOfOverflowing() {
        Probabilities p = model().predict(100_000, 0);
        assertFalse(Double.isNaN(p.home()) || Double.isNaN(p.draw()) || Double.isNaN(p.away()));
        assertEquals(1.0, p.home() + p.draw() + p.away(), 1e-12);
        assertTrue(p.home() > 0.99);
    }

    @Test
    void predictedBreaksTiesTowardsHomeThenDraw() {
        assertEquals(Outcome.HOME_WIN, new Probabilities(0.4, 0.4, 0.2).predicted());
        assertEquals(Outcome.DRAW, new Probabilities(0.2, 0.4, 0.4).predicted());
        assertEquals(Outcome.AWAY_WIN, new Probabilities(0.2, 0.3, 0.5).predicted());
    }

    @Test
    void refusesAModelFileWithTheWrongClassOrder() {
        String bad = """
                name=x
                homeAdvantage=60
                mean=0
                scale=1
                labels=H,D,A
                coef=1,2,3
                intercept=0,0,0
                """;
        assertThrows(IllegalArgumentException.class,
                () -> MatchModel.load(new ByteArrayInputStream(bad.getBytes(StandardCharsets.UTF_8))));
    }

    @Test
    void refusesAModelFileMissingAField() {
        String bad = "name=x\nlabels=A,D,H\n";
        assertThrows(IllegalArgumentException.class,
                () -> MatchModel.load(new ByteArrayInputStream(bad.getBytes(StandardCharsets.UTF_8))));
    }

    @Test
    void refusesANonPositiveScale() {
        assertThrows(IllegalArgumentException.class,
                () -> new MatchModel("x", 60, 0, 0, new double[3], new double[3]));
    }
}
