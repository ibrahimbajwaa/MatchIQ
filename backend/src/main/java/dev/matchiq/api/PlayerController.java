package dev.matchiq.api;

import dev.matchiq.api.Dtos.PlayerProfile;
import dev.matchiq.api.Dtos.PlayerSummary;
import dev.matchiq.api.Dtos.ScoutMap;
import dev.matchiq.api.Dtos.SimilarPlayer;
import dev.matchiq.service.PlayerService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class PlayerController {

    private final PlayerService players;

    public PlayerController(PlayerService players) {
        this.players = players;
    }

    @GetMapping("/players")
    public List<PlayerSummary> search(
            @RequestParam(name = "q", defaultValue = "") String q,
            @RequestParam(name = "limit", defaultValue = "8") @Min(1) @Max(25) int limit) {
        return players.search(q, limit);
    }

    @GetMapping("/players/{id}")
    public PlayerProfile profile(@PathVariable("id") int id) {
        return players.profile(id);
    }

    @GetMapping("/players/{id}/similar")
    public List<SimilarPlayer> similar(
            @PathVariable("id") int id,
            @RequestParam(name = "limit", defaultValue = "10") @Min(1) @Max(50) int limit,
            @RequestParam(name = "samePosition", defaultValue = "false") boolean samePosition) {
        return players.similar(id, limit, samePosition);
    }

    @GetMapping("/scout/map")
    public ScoutMap scoutMap() {
        return players.scoutMap();
    }
}
