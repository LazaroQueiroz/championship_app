from __future__ import annotations

from typing import Any

from app.storage import JsonRepository
from app.utils import generate_id
from app.services.player_service import PlayerService


class TeamService:
    def __init__(self, repo: JsonRepository, player_service: PlayerService):
        self.repo = repo
        self.player_service = player_service

    def _load(self) -> list[dict[str, Any]]:
        return self.repo.load()

    def _save(self, teams: list[dict[str, Any]]) -> None:
        self.repo.save(teams)

    def list_teams(self) -> list[dict[str, Any]]:
        """Return active (non-archived) teams sorted by name."""
        return sorted(
            (t for t in self._load() if not t.get("is_archived", False)),
            key=lambda t: t["name"].lower()
        )

    def list_archived_teams(self) -> list[dict[str, Any]]:
        """Return archived (historical) teams."""
        return sorted(
            (t for t in self._load() if t.get("is_archived", False)),
            key=lambda t: t["name"].lower()
        )

    def get_team(self, team_id: str) -> dict[str, Any] | None:
        for t in self._load():
            if t["id"] == team_id:
                return t
        return None

    def create_team(self, name: str, player_ids: list[str], is_draft: bool = False, championship_id: str | None = None) -> dict[str, Any]:
        teams = self._load()
        
        if not is_draft:
            if any(t["name"].strip().lower() == name.strip().lower() and not t.get("is_draft", False) and not t.get("is_archived", False) for t in teams):
                raise ValueError("Já existe um time principal com esse nome.")
                
        self._validate_players(player_ids)
        team = {
            "id": generate_id("tm"),
            "name": name.strip(),
            "player_ids": player_ids,
            "is_draft": is_draft,
            "championship_id": championship_id,
            "is_archived": False,
        }
        teams.append(team)
        self._save(teams)
        return team

    def update_team(self, team_id: str, name: str, player_ids: list[str]) -> dict[str, Any]:
        teams = self._load()
        self._validate_players(player_ids)

        # Allow duplicate names for draft teams, but not for core active teams.
        target = next((t for t in teams if t["id"] == team_id), None)
        if target and not target.get("is_draft", False):
            for t in teams:
                if t["id"] != team_id and t["name"].strip().lower() == name.strip().lower() and not t.get("is_draft", False):
                    raise ValueError("Já existe time com esse nome.")

        for t in teams:
            if t["id"] == team_id:
                t["name"] = name.strip()
                t["player_ids"] = player_ids
                self._save(teams)
                return t
        raise ValueError("Time não encontrado.")

    def delete_team(self, team_id: str) -> None:
        teams = self._load()
        updated = [t for t in teams if t["id"] != team_id]
        if len(updated) == len(teams):
            raise ValueError("Time não encontrado.")
        self._save(updated)

    def _validate_players(self, player_ids: list[str]) -> None:
        if not player_ids:
            raise ValueError("Time precisa de ao menos 1 jogador.")
        for pid in player_ids:
            if self.player_service.get_player(pid) is None:
                raise ValueError(f"Jogador {pid} não encontrado.")

    def remove_player_from_all_teams(self, player_id: str) -> None:
        teams = self._load()
        changed = False
        for t in teams:
            if player_id in t["player_ids"]:
                t["player_ids"] = [pid for pid in t["player_ids"] if pid != player_id]
                changed = True
        if changed:
            self._save(teams)

    def archive_teams_for_championship(self, championship_id: str) -> None:
        """Mark all teams belonging to a championship as archived (historical)."""
        teams = self._load()
        changed = False
        for t in teams:
            if t.get("championship_id") == championship_id and not t.get("is_archived", False):
                t["is_archived"] = True
                changed = True
        if changed:
            self._save(teams)
