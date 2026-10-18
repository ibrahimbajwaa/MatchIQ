package dev.matchiq.api;

import dev.matchiq.api.Dtos.FixtureView;
import dev.matchiq.api.Dtos.Prediction;
import dev.matchiq.api.Dtos.Team;
import dev.matchiq.api.Dtos.TeamRating;
import dev.matchiq.service.MatchService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class MatchController {

    private final MatchService matches;

    public MatchController(MatchService matches) {
        this.matches = matches;
    }

    @GetMapping("/teams")
    public List<Team> teams(@RequestParam(name = "league", defaultValue = "true") boolean league) {
        return matches.teams(league);
    }

    @GetMapping("/teams/ratings")
    public List<TeamRating> ratings() {
        return matches.ratings();
    }

    @GetMapping("/fixtures")
    public List<FixtureView> fixtures(
            @RequestParam(name = "gameweek", required = false) Integer gameweek,
            @RequestParam(name = "status", required = false) String status) {
        return matches.fixtures(gameweek, status);
    }

    @GetMapping("/predict")
    public Prediction predict(@RequestParam(name = "homeId") int homeId, @RequestParam(name = "awayId") int awayId) {
        return matches.predict(homeId, awayId);
    }
}
