from __future__ import annotations

from collections import defaultdict
from typing import Any


def generate_balanced_teams(players: list[dict[str, Any]], number_of_teams: int) -> list[dict[str, Any]]:
    """Generate balanced teams using snake draft by star rating."""
    if number_of_teams <= 0:
        raise ValueError("Número de times deve ser maior que zero.")
    if len(players) < number_of_teams:
        raise ValueError("Quantidade de jogadores insuficiente para gerar os times.")

    sorted_players = sorted(players, key=lambda p: (-p["stars"], p["name"].lower()))
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)

    direction = 1
    team_index = 0
    for player in sorted_players:
        buckets[team_index].append(player)
        if direction == 1:
            if team_index == number_of_teams - 1:
                direction = -1
            else:
                team_index += 1
        else:
            if team_index == 0:
                direction = 1
            else:
                team_index -= 1

    generated = []
    for i in range(number_of_teams):
        team_players = buckets[i]
        stars_total = sum(p["stars"] for p in team_players)
        generated.append(
            {
                "slot": i + 1,
                "players": team_players,
                "stars_total": stars_total,
                "stars_avg": round(stars_total / len(team_players), 2) if team_players else 0,
            }
        )
    return generated
