package dev.matchiq.core;

/** Win / draw / loss probabilities for one match. They always sum to 1. */
public record Probabilities(double home, double draw, double away) {

    /** The most likely result. Ties go to the home side, then the draw. */
    public Outcome predicted() {
        if (home >= draw && home >= away) {
            return Outcome.HOME_WIN;
        }
        return draw >= away ? Outcome.DRAW : Outcome.AWAY_WIN;
    }
}
