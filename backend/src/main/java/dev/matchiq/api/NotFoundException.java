package dev.matchiq.api;

/** The thing asked for does not exist. Becomes a 404. */
public class NotFoundException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public NotFoundException(String message) {
        super(message);
    }
}
