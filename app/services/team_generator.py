from __future__ import annotations

from collections import defaultdict
from typing import Any


import random

COLORS = [
    "Azul", "Vermelho", "Verde", "Amarelo", "Branco",
    "Preto", "Laranja", "Roxo", "Cinza", "Rosa", "Marrom", "Ciano"
]

def generate_balanced_teams(players: list[dict[str, Any]], number_of_teams: int) -> list[dict[str, Any]]:
    """Generate balanced teams using snake draft by star rating."""
    if number_of_teams <= 0:
        raise ValueError("Número de times deve ser maior que zero.")
    if len(players) < number_of_teams:
        raise ValueError("Quantidade de jogadores insuficiente para gerar os times.")

    players_by_star = defaultdict(list)
    for p in players:
        players_by_star[p["stars"]].append(p)

    sorted_players = []
    for star in sorted(players_by_star.keys(), reverse=True):
        group = players_by_star[star]
        random.shuffle(group)
        sorted_players.extend(group)
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
        
        color_name = COLORS[i % len(COLORS)]
        if i >= len(COLORS):
            color_name = f"{color_name} {i + 1}"
            
        stars_total = sum(p["stars"] for p in team_players)
        generated.append(
            {
                "slot": i + 1,
                "name": f"Time {color_name}",
                "players": team_players,
                "stars_total": stars_total,
                "stars_avg": round(stars_total / len(team_players), 2) if team_players else 0,
            }
        )
    return generated
