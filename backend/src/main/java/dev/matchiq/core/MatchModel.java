package dev.matchiq.core;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Properties;

/**
 * The match predictor, ported from the Python pipeline: a multinomial logistic regression with one input,
 * the Elo difference (home rating + home advantage - away rating).
 *
 * <pre>
 *   x       = (eloDiff - mean) / scale            // the standard scaler fitted in training
 *   score_c = coef_c * x + intercept_c            // one score per class, in the order A, D, H
 *   p       = softmax(score)
 * </pre>
 *
 * The coefficients come from {@code elo_logit.properties}, written by {@code pipeline/src/export.py}. A test checks this
 * class against probabilities computed by scikit-learn, so the Java and Python versions cannot drift apart.
 */
public final class MatchModel {

    private static final int AWAY = 0;
    private static final int DRAW = 1;
    private static final int HOME = 2;

    private final String name;
    private final double homeAdvantage;
    private final double mean;
    private final double scale;
    private final double[] coef;
    private final double[] intercept;

    public MatchModel(String name, double homeAdvantage, double mean, double scale, double[] coef, double[] intercept) {
        if (coef.length != 3 || intercept.length != 3) {
            throw new IllegalArgumentException("expected one coefficient and one intercept per class (A, D, H)");
        }
        if (!(scale > 0)) {
            throw new IllegalArgumentException("scale must be positive, got " + scale);
        }
        this.name = name;
        this.homeAdvantage = homeAdvantage;
        this.mean = mean;
        this.scale = scale;
        this.coef = coef.clone();
        this.intercept = intercept.clone();
    }

    public static MatchModel load(InputStream in) {
        Properties p = new Properties();
        try {
            p.load(in);
        } catch (IOException e) {
            throw new UncheckedIOException("could not read the match model", e);
        }
        String[] labels = required(p, "labels").split(",");
        if (!String.join(",", labels).equals("A,D,H")) {
            throw new IllegalArgumentException("class order must be A,D,H but was " + String.join(",", labels));
        }
        return new MatchModel(
                required(p, "name"),
                Double.parseDouble(required(p, "homeAdvantage")),
                Double.parseDouble(required(p, "mean")),
                Double.parseDouble(required(p, "scale")),
                doubles(required(p, "coef")),
                doubles(required(p, "intercept")));
    }

    public Probabilities predict(double homeElo, double awayElo) {
        double x = (homeElo + homeAdvantage - awayElo - mean) / scale;
        double[] score = new double[3];
        double max = Double.NEGATIVE_INFINITY;
        for (int c = 0; c < 3; c++) {
            score[c] = coef[c] * x + intercept[c];
            max = Math.max(max, score[c]);
        }
        // Subtracting the max keeps exp() from overflowing for extreme rating gaps.
        double sum = 0;
        for (int c = 0; c < 3; c++) {
            score[c] = Math.exp(score[c] - max);
            sum += score[c];
        }
        return new Probabilities(score[HOME] / sum, score[DRAW] / sum, score[AWAY] / sum);
    }

    public String name() {
        return name;
    }

    public double homeAdvantage() {
        return homeAdvantage;
    }

    private static String required(Properties p, String key) {
        String v = p.getProperty(key);
        if (v == null) {
            throw new IllegalArgumentException("model file is missing '" + key + "'");
        }
        return v.trim();
    }

    private static double[] doubles(String csv) {
        String[] parts = csv.split(",");
        double[] out = new double[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Double.parseDouble(parts[i].trim());
        }
        return out;
    }
}
