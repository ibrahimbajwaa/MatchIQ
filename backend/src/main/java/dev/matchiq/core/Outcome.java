package dev.matchiq.core;

/** Result of a match from the home side's point of view. */
public enum Outcome {
    HOME_WIN('H'), DRAW('D'), AWAY_WIN('A');

    private final char code;

    Outcome(char code) {
        this.code = code;
    }

    /** The one-letter code used in the data and the API: H, D or A. */
    public char code() {
        return code;
    }
}
