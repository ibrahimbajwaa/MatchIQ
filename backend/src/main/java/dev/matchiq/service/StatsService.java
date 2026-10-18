package dev.matchiq.service;

import dev.matchiq.api.Dtos.Headline;
import dev.matchiq.api.Dtos.LeaderboardEntry;
import dev.matchiq.api.Dtos.LeaderboardPage;
import dev.matchiq.api.Dtos.ModelMetric;
import dev.matchiq.api.Dtos.ModelReport;
import dev.matchiq.api.Dtos.Overview;
import dev.matchiq.api.Dtos.StatDef;
import dev.matchiq.api.NotFoundException;
import dev.matchiq.core.BoardKey;
import dev.matchiq.core.Leaderboards;
import dev.matchiq.store.ModelRepository;
import dev.matchiq.store.PlayerRepository;
import dev.matchiq.store.PlayerRepository.PlayerStat;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class StatsService {

    private static final String BASELINE_MODEL = "Always home win";

    private final PlayerRepository players;
    private final ModelRepository model;
    private final Leaderboards leaderboards;
    private final List<StatDef> statDefs;
    private final Map<String, StatDef> statByKey;

    public StatsService(PlayerRepository players, ModelRepository model, Leaderboards leaderboards) {
        this.players = players;
        this.model = model;
        this.leaderboards = leaderboards;
        this.statDefs = List.copyOf(players.statDefs());   // fixed for the life of the process; a re-seed restarts it
        this.statByKey = statDefs.stream().collect(Collectors.toMap(StatDef::key, Function.identity()));
    }

    public List<StatDef> stats() {
        return statDefs;
    }

    public LeaderboardPage leaderboard(String statKey, String scopeText, int offset, int limit) {
        StatDef stat = statByKey.get(statKey);
        if (stat == null) {
            throw new NotFoundException("Unknown stat '" + statKey + "'");
        }
        String scope = Scopes.normalize(scopeText);
        Leaderboards.Page page = leaderboards.page(new BoardKey(statKey, scope), offset, limit);
        Map<Integer, PlayerStat> details = players.findWithStat(statKey,
                page.entries().stream().map(Leaderboards.RankedEntry::playerId).toList());
        List<LeaderboardEntry> entries = new ArrayList<>(page.entries().size());
        for (Leaderboards.RankedEntry e : page.entries()) {
            PlayerStat d = details.get(e.playerId());
            if (d != null) {
                entries.add(new LeaderboardEntry(e.rank(), d.player(), d.per90(), d.raw()));
            }
        }
        return new LeaderboardPage(statKey, stat.label(), scope, page.total(), offset, limit, entries);
    }

    public Overview overview() {
        ModelRepository.Totals totals = model.totals();
        Map<String, Object> meta = model.meta();
        List<ModelMetric> metrics = model.metrics();
        ModelMetric chosen = metrics.stream().filter(ModelMetric::chosen).findFirst().orElseThrow();
        ModelMetric baseline = metrics.stream().filter(m -> m.model().equals(BASELINE_MODEL)).findFirst().orElseThrow();
        int testMatches = ((Number) meta.get("testMatches")).intValue();
        return new Overview(meta, totals.counts(), totals.nextGameweek(),
                new Headline(chosen.model(), chosen.accuracy(), baseline.accuracy(), testMatches));
    }

    public ModelReport modelReport() {
        List<ModelMetric> metrics = model.metrics();
        String chosen = metrics.stream().filter(ModelMetric::chosen).findFirst().orElseThrow().model();
        return new ModelReport(chosen, metrics, model.seasons(), model.meta());
    }
}
