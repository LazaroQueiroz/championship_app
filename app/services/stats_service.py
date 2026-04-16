from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.services.team_service import TeamService
from app.services.player_service import PlayerService


class StatsService:
    def __init__(self, player_service: PlayerService, team_service: TeamService):
        self.player_service = player_service
        self.team_service = team_service

    def aggregate(self, championships: list[dict[str, Any]]) -> dict[str, Any]:
        player_goals = Counter()
        team_titles = Counter()
        goals_per_championship = []
        phase_goals = defaultdict(int)

        for ch in championships:
            total_goals = 0
            for match in ch.get("matches", []):
                if not match.get("is_played"):
                    continue
                total_goals += match.get("goals_home", 0) + match.get("goals_away", 0)
                phase_goals[match.get("phase", "unknown")] += match.get("goals_home", 0) + match.get("goals_away", 0)
                for g in match.get("goals_by_player", []):
                    player_goals[g["player_id"]] += 1

            goals_per_championship.append(
                {"championship_id": ch["id"], "name": ch["name"], "created_at": ch["created_at"], "total_goals": total_goals}
            )

            champion = ch.get("knockout", {}).get("champion_team_id")
            if champion:
                team_titles[champion] += 1

        top_players = []
        for player_id, goals in player_goals.most_common(20):
            player = self.player_service.get_player(player_id)
            top_players.append({"player_id": player_id, "player_name": player["name"] if player else player_id, "goals": goals})

        top_teams = []
        for team_id, titles in team_titles.most_common(20):
            team = self.team_service.get_team(team_id)
            top_teams.append({"team_id": team_id, "team_name": team["name"] if team else team_id, "titles": titles})

        goals_per_championship.sort(key=lambda x: x["created_at"])
        trend = []
        prev = None
        for row in goals_per_championship:
            if prev is None:
                trend.append({**row, "delta_vs_previous": None})
            else:
                trend.append({**row, "delta_vs_previous": row["total_goals"] - prev})
            prev = row["total_goals"]

        return {
            "championship_count": len(championships),
            "best_player": top_players[0] if top_players else None,
            "top_players": top_players,
            "top_teams_by_titles": top_teams,
            "goals_by_phase": dict(phase_goals),
            "historical_trend": trend,
        }
