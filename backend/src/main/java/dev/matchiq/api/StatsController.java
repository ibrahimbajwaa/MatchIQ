package dev.matchiq.api;

import dev.matchiq.api.Dtos.LeaderboardPage;
import dev.matchiq.api.Dtos.ModelReport;
import dev.matchiq.api.Dtos.Overview;
import dev.matchiq.api.Dtos.StatDef;
import dev.matchiq.service.StatsService;
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
public class StatsController {

    private final StatsService stats;

    public StatsController(StatsService stats) {
        this.stats = stats;
    }

    @GetMapping("/overview")
    public Overview overview() {
        return stats.overview();
    }

    @GetMapping("/stats")
    public List<StatDef> stats() {
        return stats.stats();
    }

    @GetMapping("/leaderboards/{statKey}")
    public LeaderboardPage leaderboard(
            @PathVariable("statKey") String statKey,
            @RequestParam(name = "scope", defaultValue = "all") String scope,
            @RequestParam(name = "offset", defaultValue = "0") @Min(0) int offset,
            @RequestParam(name = "limit", defaultValue = "25") @Min(1) @Max(100) int limit) {
        return stats.leaderboard(statKey, scope, offset, limit);
    }

    @GetMapping("/model")
    public ModelReport model() {
        return stats.modelReport();
    }
}
