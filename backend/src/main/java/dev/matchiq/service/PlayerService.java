package dev.matchiq.service;

import dev.matchiq.api.Dtos.MapPoint;
import dev.matchiq.api.Dtos.PlayerProfile;
import dev.matchiq.api.Dtos.PlayerSummary;
import dev.matchiq.api.Dtos.ScoutMap;
import dev.matchiq.api.Dtos.SimilarPlayer;
import dev.matchiq.api.Dtos.StatLine;
import dev.matchiq.api.NotFoundException;
import dev.matchiq.core.BoardKey;
import dev.matchiq.core.Leaderboards;
import dev.matchiq.core.SimilarityIndex;
import dev.matchiq.store.PlayerRepository;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import org.springframework.stereotype.Service;

@Service
public class PlayerService {

    private final PlayerRepository players;
    private final SimilarityIndex index;
    private final Leaderboards leaderboards;
    private final Timer similarityTimer;

    public PlayerService(PlayerRepository players, SimilarityIndex index, Leaderboards leaderboards,
                         MeterRegistry meters) {
        this.players = players;
        this.index = index;
        this.leaderboards = leaderboards;
        this.similarityTimer = Timer.builder("matchiq.similarity.query")
                .description("Time to find the most similar players in the in-memory index")
                .register(meters);
    }

    public List<PlayerSummary> search(String text, int limit) {
        String trimmed = text == null ? "" : text.trim();
        return trimmed.isEmpty() ? List.of() : players.search(trimmed, limit);
    }

    public PlayerProfile profile(int id) {
        PlayerSummary player = require(id);
        List<StatLine> lines = new ArrayList<>();
        for (PlayerRepository.StatRow s : players.stats(id)) {
            // Rank among players in the same position, taken from the leaderboards.
            var rank = leaderboards.rankOf(new BoardKey(s.key(), player.position()), id);
            lines.add(new StatLine(s.key(), s.label(), s.description(), s.raw(), s.per90(), s.percentile(),
                    rank.map(Leaderboards.PlayerRank::rank).orElse(null),
                    rank.map(Leaderboards.PlayerRank::outOf).orElse(null)));
        }
        return new PlayerProfile(player, lines);
    }

    public List<SimilarPlayer> similar(int id, int limit, boolean samePositionOnly) {
        require(id);
        if (!index.contains(id)) {
            throw new NotFoundException("No stats to compare for player " + id);
        }
        List<SimilarityIndex.Neighbor> neighbours =
                similarityTimer.record(() -> index.mostSimilar(id, limit, samePositionOnly));
        Map<Integer, PlayerSummary> byId = players.findAll(neighbours.stream().map(SimilarityIndex.Neighbor::id).toList());
        List<SimilarPlayer> out = new ArrayList<>(neighbours.size());
        for (SimilarityIndex.Neighbor n : neighbours) {
            PlayerSummary p = byId.get(n.id());
            if (p != null) {
                out.add(new SimilarPlayer(p, n.similarity()));
            }
        }
        return out;
    }

    public ScoutMap scoutMap() {
        List<MapPoint> points = players.scoutMap();
        TreeSet<String> styles = new TreeSet<>();
        points.forEach(p -> styles.add(p.style()));
        return new ScoutMap(List.copyOf(styles), points);
    }

    private PlayerSummary require(int id) {
        return players.find(id).orElseThrow(() -> new NotFoundException("No player with id " + id));
    }
}
