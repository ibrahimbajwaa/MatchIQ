package dev.matchiq.service;

import dev.matchiq.api.BadRequestException;
import dev.matchiq.api.Dtos.EloPoint;
import dev.matchiq.api.Dtos.FixtureView;
import dev.matchiq.api.Dtos.Prediction;
import dev.matchiq.api.Dtos.Team;
import dev.matchiq.api.Dtos.TeamRating;
import dev.matchiq.api.Dtos.TeamSide;
import dev.matchiq.api.NotFoundException;
import dev.matchiq.core.MatchModel;
import dev.matchiq.core.Probabilities;
import dev.matchiq.store.FixtureRepository;
import dev.matchiq.store.TeamRepository;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class MatchService {

    private static final Set<String> STATUSES = Set.of("UPCOMING", "FINISHED");

    private final TeamRepository teams;
    private final FixtureRepository fixtures;
    private final MatchModel model;

    public MatchService(TeamRepository teams, FixtureRepository fixtures, MatchModel model) {
        this.teams = teams;
        this.fixtures = fixtures;
        this.model = model;
    }

    public List<Team> teams(boolean leagueOnly) {
        List<Team> all = teams.all();
        return leagueOnly ? all.stream().filter(Team::inLeague).toList() : all;
    }

    /** This season's teams, strongest first, each with its Elo rating over time. */
    public List<TeamRating> ratings() {
        Map<Integer, List<EloPoint>> history = teams.eloHistory();
        return teams(true).stream()
                .map(t -> new TeamRating(t.id(), t.name(), t.displayName(), t.shortName(), t.elo(), t.eloRank(),
                        t.inLeague(), history.getOrDefault(t.id(), List.of())))
                .toList();
    }

    public List<FixtureView> fixtures(Integer gameweek, String status) {
        String normalized = status == null ? null : status.toUpperCase();
        if (normalized != null && !STATUSES.contains(normalized)) {
            throw new BadRequestException("Unknown status '" + status + "'. Use UPCOMING or FINISHED.");
        }
        return fixtures.find(gameweek, normalized);
    }

    /** Predicts any pairing with the Java port of the Python model, from the teams' current Elo ratings. */
    public Prediction predict(int homeId, int awayId) {
        if (homeId == awayId) {
            throw new BadRequestException("Pick two different teams");
        }
        Team home = teams.find(homeId).orElseThrow(() -> new NotFoundException("No team with id " + homeId));
        Team away = teams.find(awayId).orElseThrow(() -> new NotFoundException("No team with id " + awayId));
        Probabilities p = model.predict(home.elo(), away.elo());
        return new Prediction(side(home), side(away), p.home(), p.draw(), p.away(),
                String.valueOf(p.predicted().code()), model.homeAdvantage(),
                home.elo() + model.homeAdvantage() - away.elo(), model.name());
    }

    private static TeamSide side(Team t) {
        return new TeamSide(t.id(), t.shortName(), t.displayName(), t.elo());
    }
}
