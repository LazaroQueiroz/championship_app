from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.storage import JsonRepository
from app.utils import generate_id


@dataclass
class Player:
    id: str
    name: str
    stars: int


class PlayerService:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def _load(self) -> list[dict[str, Any]]:
        return self.repo.load()

    def _save(self, players: list[dict[str, Any]]) -> None:
        self.repo.save(players)

    def list_players(self) -> list[dict[str, Any]]:
        return sorted(self._load(), key=lambda p: p["name"].lower())

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        for p in self._load():
            if p["id"] == player_id:
                return p
        return None

    def create_player(self, name: str, stars: int) -> dict[str, Any]:
        players = self._load()
        if any(p["name"].strip().lower() == name.strip().lower() for p in players):
            raise ValueError("Já existe jogador com esse nome.")
        if not (0 <= stars <= 5):
            raise ValueError("Estrelas devem estar entre 0 e 5.")

        player = {"id": generate_id("ply"), "name": name.strip(), "stars": stars}
        players.append(player)
        self._save(players)
        return player

    def update_player(self, player_id: str, name: str, stars: int) -> dict[str, Any]:
        players = self._load()
        if not (0 <= stars <= 5):
            raise ValueError("Estrelas devem estar entre 0 e 5.")

        for p in players:
            if p["id"] != player_id and p["name"].strip().lower() == name.strip().lower():
                raise ValueError("Já existe jogador com esse nome.")

        for p in players:
            if p["id"] == player_id:
                p["name"] = name.strip()
                p["stars"] = stars
                self._save(players)
                return p
        raise ValueError("Jogador não encontrado.")

    def delete_player(self, player_id: str) -> None:
        players = self._load()
        updated = [p for p in players if p["id"] != player_id]
        if len(updated) == len(players):
            raise ValueError("Jogador não encontrado.")
        self._save(updated)
