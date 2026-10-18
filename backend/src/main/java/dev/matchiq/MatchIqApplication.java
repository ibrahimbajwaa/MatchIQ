package dev.matchiq;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MatchIqApplication {

    public static void main(String[] args) {
        SpringApplication.run(MatchIqApplication.class, args);
    }
}
