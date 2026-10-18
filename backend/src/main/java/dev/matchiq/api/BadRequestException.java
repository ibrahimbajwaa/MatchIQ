package dev.matchiq.api;

/** The request itself is wrong (unknown scope, same team twice, ...). Becomes a 400. */
public class BadRequestException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public BadRequestException(String message) {
        super(message);
    }
}
