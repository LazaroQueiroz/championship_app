from __future__ import annotations

from itertools import combinations
from math import ceil, log2
from typing import Any

from app.storage import JsonRepository
from app.utils import generate_id, now_iso
from app.services.team_service import TeamService


class ChampionshipService:
    def __init__(self, repo: JsonRepository, team_service: TeamService):
        self.repo = repo
        self.team_service = team_service

    def _load(self) -> list[dict[str, Any]]:
        return self.repo.load()

    def _save(self, championships: list[dict[str, Any]]) -> None:
        self.repo.save(championships)

    def list_championships(self) -> list[dict[str, Any]]:
        champs = self._load()
        return sorted(champs, key=lambda c: c["created_at"], reverse=True)

    def get_championship(self, championship_id: str) -> dict[str, Any] | None:
        for c in self._load():
            if c["id"] == championship_id:
                return c
        return None

    def delete_championship(self, championship_id: str) -> None:
        champs = self._load()
        champs = [c for c in champs if c["id"] != championship_id]
        self._save(champs)

    def create_championship(
        self,
        name: str,
        team_ids: list[str],
        number_of_groups: int,
        match_duration_minutes: int,
    ) -> dict[str, Any]:
        if len(team_ids) < 2:
            raise ValueError("É necessário no mínimo 2 times.")
        if number_of_groups <= 0:
            raise ValueError("Número de grupos deve ser maior que 0.")
        if number_of_groups > len(team_ids):
            raise ValueError("Número de grupos não pode exceder quantidade de times.")
        if match_duration_minutes <= 0:
            raise ValueError("Duração da partida deve ser maior que 0.")

        self._validate_team_ids(team_ids)

        groups = self._build_groups(team_ids, number_of_groups)
        matches = []

        for group in groups:
            group_matches = self._build_round_robin_matches(group["team_ids"], "group", group["name"])
            matches.extend(group_matches)
            group["match_ids"] = [m["id"] for m in group_matches]
            group["standings"] = {
                tid: {
                    "team_id": tid,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "gf": 0,
                    "ga": 0,
                    "gd": 0,
                    "points": 0,
                }
                for tid in group["team_ids"]
            }

        matches = self._reorder_matches_no_consecutive_teams(matches)
        for i, match in enumerate(matches, start=1):
            match["schedule_order"] = i
            match["duration_minutes"] = match_duration_minutes

        championship = {
            "id": generate_id("chp"),
            "name": name.strip(),
            "created_at": now_iso(),
            "status": "group_stage",
            "config": {
                "number_of_groups": number_of_groups,
                "match_duration_minutes": match_duration_minutes,
                "qualifiers_per_group": None,
            },
            "team_ids": team_ids,
            "groups": groups,
            "matches": matches,
            "knockout": {"rounds": [], "champion_team_id": None},
        }

        championships = self._load()
        championships.append(championship)
        self._save(championships)
        return championship

    def record_match_result(
        self,
        championship_id: str,
        match_id: str,
        goals_by_player: list[dict[str, Any]],
        penalties_home: int | None = None,
        penalties_away: int | None = None,
        penalties_by_player: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        championships = self._load()
        ch = self._must_find_championship(championships, championship_id)
        match = self._must_find_match(ch, match_id)

        if match["is_played"]:
            raise ValueError("Partida já registrada.")

        home_goals = sum(1 for g in goals_by_player if g["team_id"] == match["home_team_id"])
        away_goals = sum(1 for g in goals_by_player if g["team_id"] == match["away_team_id"])

        match["is_played"] = True
        match["goals_home"] = home_goals
        match["goals_away"] = away_goals
        match["goals_by_player"] = goals_by_player
        match["penalties_home"] = penalties_home
        match["penalties_away"] = penalties_away
        match["penalties_by_player"] = penalties_by_player or []
        match["played_at"] = now_iso()

        winner_team_id = None
        if match["phase"] == "knockout":
            if home_goals == away_goals:
                if penalties_home is None or penalties_away is None:
                    raise ValueError("No mata-mata, empate exige o número de gols de pênalti.")
                if penalties_home == penalties_away:
                    raise ValueError("No mata-mata, os gols de pênalti não podem ser iguais.")
                winner_team_id = match["home_team_id"] if penalties_home > penalties_away else match["away_team_id"]
            else:
                winner_team_id = match["home_team_id"] if home_goals > away_goals else match["away_team_id"]
            match["winner_team_id"] = winner_team_id

        if match["phase"] == "group":
            self._update_group_standings(ch, match)
            if self._all_group_matches_played(ch):
                ch["status"] = "group_finished"

        if match["phase"] == "knockout":
            self._advance_knockout_if_possible(ch)

        self._save(championships)
        return match

    def edit_match_result(
        self,
        championship_id: str,
        match_id: str,
        goals_by_player: list[dict[str, Any]],
        penalties_home: int | None = None,
        penalties_away: int | None = None,
        penalties_by_player: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        championships = self._load()
        ch = self._must_find_championship(championships, championship_id)
        match = self._must_find_match(ch, match_id)

        if not match["is_played"]:
            raise ValueError("Não é possível editar uma partida que ainda não foi jogada.")

        if match["phase"] == "knockout":
            current_round_idx = next(
                (i for i, r in enumerate(ch["knockout"]["rounds"]) if match_id in r["match_ids"]), None
            )
            if current_round_idx is not None and current_round_idx < len(ch["knockout"]["rounds"]) - 1:
                raise ValueError("Inviável editar este jogo: as próximas chaves do mata-mata já foram giradas.")

        home_goals = sum(1 for g in goals_by_player if g["team_id"] == match["home_team_id"])
        away_goals = sum(1 for g in goals_by_player if g["team_id"] == match["away_team_id"])

        match["goals_home"] = home_goals
        match["goals_away"] = away_goals
        match["goals_by_player"] = goals_by_player
        match["penalties_home"] = penalties_home
        match["penalties_away"] = penalties_away
        match["penalties_by_player"] = penalties_by_player or []

        if match["phase"] == "knockout":
            if home_goals == away_goals:
                if penalties_home is None or penalties_away is None:
                    raise ValueError("Empate em mata-mata requer o número de gols de pênalti.")
                if penalties_home == penalties_away:
                    raise ValueError("No mata-mata, os gols de pênalti não podem ser iguais.")
                match["winner_team_id"] = match["home_team_id"] if penalties_home > penalties_away else match["away_team_id"]
            else:
                match["winner_team_id"] = match["home_team_id"] if home_goals > away_goals else match["away_team_id"]
            
            self._advance_knockout_if_possible(ch)
            
        elif match["phase"] == "group":
            self._recalculate_group_standings(ch)

        self._save(championships)
        return match

    def delete_match(self, championship_id: str, match_id: str) -> None:
        championships = self._load()
        ch = self._must_find_championship(championships, championship_id)
        match = self._must_find_match(ch, match_id)

        if match["phase"] == "knockout":
            raise ValueError("Não é permitido excluir partidas de mata-mata. Edite-as se necessário.")

        ch["matches"] = [m for m in ch["matches"] if m["id"] != match_id]
        
        for g in ch.get("groups", []):
            if match_id in g["match_ids"]:
                g["match_ids"].remove(match_id)
                
        self._recalculate_group_standings(ch)
        self._save(championships)

    def create_knockout(self, championship_id: str, qualifiers_per_group: int) -> dict[str, Any]:
        championships = self._load()
        ch = self._must_find_championship(championships, championship_id)

        if not self._all_group_matches_played(ch):
            raise ValueError("Ainda há partidas pendentes na fase de grupos.")
        if ch["knockout"]["rounds"]:
            raise ValueError("Mata-mata já foi gerado para este campeonato.")

        qualifiers = self._get_qualifiers(ch, qualifiers_per_group)
        if len(qualifiers) < 2:
            raise ValueError("Quantidade de classificados insuficiente para mata-mata.")

        full_size = 2 ** ceil(log2(len(qualifiers)))
        byes = full_size - len(qualifiers)

        seeds = qualifiers[:] + [None] * byes

        # Gerar posições da chave no formato tradicional de mata-mata
        def generate_bracket(n: int) -> list[int]:
            if n <= 1:
                return [1]
            matches = [1, 2]
            for _ in range(1, int(log2(n))):
                next_matches = []
                length = len(matches) * 2
                for seed in matches:
                    next_matches.append(seed)
                    next_matches.append(length + 1 - seed)
                matches = next_matches
            return matches

        bracket_positions = generate_bracket(full_size)
        pairings = []
        for i in range(0, full_size, 2):
            top_seed_idx = bracket_positions[i] - 1
            bot_seed_idx = bracket_positions[i+1] - 1
            pairings.append((seeds[top_seed_idx], seeds[bot_seed_idx]))

        first_round_name = self._round_name(len(pairings) * 2)
        round_matches = []
        next_order = self._next_schedule_order(ch)
        for home, away in pairings:
            match = {
                "id": generate_id("mch"),
                "phase": "knockout",
                "round_name": first_round_name,
                "group_name": None,
                "home_team_id": home,
                "away_team_id": away,
                "duration_minutes": ch["config"]["match_duration_minutes"],
                "is_played": home is None or away is None,
                "goals_home": 0,
                "goals_away": 0,
                "goals_by_player": [],
                "played_at": now_iso() if (home is None or away is None) else None,
                "winner_team_id": home if away is None else away if home is None else None,
                "schedule_order": next_order,
            }
            next_order += 1
            round_matches.append(match)

        ch["knockout"]["rounds"].append({"name": first_round_name, "match_ids": [m["id"] for m in round_matches]})
        ch["matches"].extend(round_matches)
        ch["config"]["qualifiers_per_group"] = qualifiers_per_group
        ch["status"] = "knockout"

        self._advance_knockout_if_possible(ch)
        self._save(championships)
        return ch

    def get_unplayed_matches(self, championship_id: str) -> list[dict[str, Any]]:
        ch = self.get_championship(championship_id)
        if not ch:
            raise ValueError("Campeonato não encontrado.")
        return sorted([m for m in ch["matches"] if not m["is_played"]], key=lambda x: x["schedule_order"])

    def _validate_team_ids(self, team_ids: list[str]) -> None:
        for tid in team_ids:
            if self.team_service.get_team(tid) is None:
                raise ValueError(f"Time {tid} não encontrado.")

    def _build_groups(self, team_ids: list[str], number_of_groups: int) -> list[dict[str, Any]]:
        group_names = [chr(ord("A") + i) for i in range(number_of_groups)]
        groups = [{"name": n, "team_ids": [], "match_ids": [], "standings": {}} for n in group_names]
        for i, tid in enumerate(team_ids):
            groups[i % number_of_groups]["team_ids"].append(tid)
        return groups

    def _build_round_robin_matches(self, team_ids: list[str], phase: str, group_name: str | None) -> list[dict[str, Any]]:
        matches = []
        for home, away in combinations(team_ids, 2):
            matches.append(
                {
                    "id": generate_id("mch"),
                    "phase": phase,
                    "round_name": None,
                    "group_name": group_name,
                    "home_team_id": home,
                    "away_team_id": away,
                    "is_played": False,
                    "goals_home": 0,
                    "goals_away": 0,
                    "goals_by_player": [],
                    "played_at": None,
                    "winner_team_id": None,
                    "schedule_order": 0,
                }
            )
        return matches

    def _reorder_matches_no_consecutive_teams(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Schedule matches so that no team plays in two consecutive slots
        and the gap between a team's successive matches is as large as possible.

        Algorithm:
        - Maintain a dict tracking the last slot index each team appeared in.
        - At each step, score every remaining match by computing the minimum
          distance (in slots) since either of its teams last played.
          A team that hasn't played yet gets distance = infinity.
        - Pick the match with the largest minimum distance (i.e., the match
          whose most-recently-seen team is furthest back).
        - Ties are broken by preferring matches whose teams have played
          the fewest total matches so far (keeps workload even).
        """
        if not matches:
            return []

        pending = list(range(len(matches)))
        ordered: list[dict[str, Any]] = []

        last_slot: dict[str, int] = {}       # team_id -> last slot index they appeared in
        play_count: dict[str, int] = {}      # team_id -> number of matches scheduled so far

        for slot in range(len(matches)):
            best_idx = None
            best_min_dist = -1
            best_total_plays = float('inf')

            for pi in pending:
                m = matches[pi]
                h = m["home_team_id"]
                a = m["away_team_id"]

                dist_h = (slot - last_slot[h]) if h in last_slot else float('inf')
                dist_a = (slot - last_slot[a]) if a in last_slot else float('inf')
                min_dist = min(dist_h, dist_a)

                total_plays = play_count.get(h, 0) + play_count.get(a, 0)

                # Primary: maximize minimum distance (avoid consecutive)
                # Secondary: prefer teams that have played less (balanced workload)
                if (min_dist > best_min_dist) or (min_dist == best_min_dist and total_plays < best_total_plays):
                    best_min_dist = min_dist
                    best_total_plays = total_plays
                    best_idx = pi

            pending.remove(best_idx)
            chosen = matches[best_idx]
            ordered.append(chosen)

            h = chosen["home_team_id"]
            a = chosen["away_team_id"]
            last_slot[h] = slot
            last_slot[a] = slot
            play_count[h] = play_count.get(h, 0) + 1
            play_count[a] = play_count.get(a, 0) + 1

        return ordered

    def _update_group_standings(self, championship: dict[str, Any], match: dict[str, Any]) -> None:
        group = next(g for g in championship["groups"] if g["name"] == match["group_name"])
        home = group["standings"][match["home_team_id"]]
        away = group["standings"][match["away_team_id"]]

        home["played"] += 1
        away["played"] += 1
        home["gf"] += match["goals_home"]
        home["ga"] += match["goals_away"]
        away["gf"] += match["goals_away"]
        away["ga"] += match["goals_home"]

        home["gd"] = home["gf"] - home["ga"]
        away["gd"] = away["gf"] - away["ga"]

        if match["goals_home"] > match["goals_away"]:
            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1
        elif match["goals_home"] < match["goals_away"]:
            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    def _recalculate_group_standings(self, championship: dict[str, Any]) -> None:
        for group in championship["groups"]:
            for standing in group["standings"].values():
                standing.update({"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0})
                
        group_matches = [m for m in championship["matches"] if m["phase"] == "group" and m["is_played"]]
        for match in group_matches:
            self._update_group_standings(championship, match)

    def _all_group_matches_played(self, championship: dict[str, Any]) -> bool:
        group_matches = [m for m in championship["matches"] if m["phase"] == "group"]
        return all(m["is_played"] for m in group_matches)

    def _sort_group_standings(self, standings: dict[str, Any]) -> list[dict[str, Any]]:
        rows = list(standings.values())
        return sorted(rows, key=lambda r: (-r["points"], -r["gd"], r["team_id"]))

    def _get_qualifiers(self, championship: dict[str, Any], qualifiers_per_group: int) -> list[str]:
        qualifiers = []
        for group in championship["groups"]:
            ranking = self._sort_group_standings(group["standings"])
            selected = ranking[:qualifiers_per_group]
            qualifiers.extend([row["team_id"] for row in selected])
        return qualifiers

    def _next_schedule_order(self, championship: dict[str, Any]) -> int:
        if not championship["matches"]:
            return 1
        return max(m["schedule_order"] for m in championship["matches"]) + 1

    def update_round_duration(self, championship_id: str, round_name: str, duration: int) -> None:
        championships = self._load()
        ch = self._must_find_championship(championships, championship_id)
        if "knockout" not in ch or not ch["knockout"]["rounds"]:
            return
            
        r = next((r for r in ch["knockout"]["rounds"] if r["name"] == round_name), None)
        if not r:
            return
            
        for mid in r["match_ids"]:
            m = self._must_find_match(ch, mid)
            m["duration_minutes"] = duration
            
        self._save(championships)

    def _advance_knockout_if_possible(self, championship: dict[str, Any]) -> None:
        rounds = championship["knockout"]["rounds"]
        if not rounds:
            return

        latest_round = rounds[-1]
        latest_matches = [self._must_find_match(championship, mid) for mid in latest_round["match_ids"]]
        if not all(m["is_played"] and m["winner_team_id"] for m in latest_matches):
            return

        winners = [m["winner_team_id"] for m in latest_matches]
        if len(winners) == 1:
            championship["status"] = "finished"
            championship["knockout"]["champion_team_id"] = winners[0]
            # Archive all teams that belonged to this championship.
            self.team_service.archive_teams_for_championship(championship["id"])
            return

        if len(winners) % 2 != 0:
            winners.append(None)

        next_round_pairs = []
        while winners:
            a = winners.pop(0)
            b = winners.pop(0)
            next_round_pairs.append((a, b))

        next_round_name = self._round_name(len(next_round_pairs) * 2)
        new_matches = []
        for a, b in next_round_pairs:
            match = {
                "id": generate_id("mch"),
                "phase": "knockout",
                "round_name": next_round_name,
                "group_name": None,
                "home_team_id": a,
                "away_team_id": b,
                "duration_minutes": championship["config"]["match_duration_minutes"],
                "is_played": a is None or b is None,
                "goals_home": 0,
                "goals_away": 0,
                "goals_by_player": [],
                "played_at": now_iso() if (a is None or b is None) else None,
                "winner_team_id": a if b is None else b if a is None else None,
                "schedule_order": self._next_schedule_order(championship),
            }
            new_matches.append(match)
            championship["matches"].append(match)

        rounds.append({"name": next_round_name, "match_ids": [m["id"] for m in new_matches]})

        if all(m["is_played"] for m in new_matches):
            self._advance_knockout_if_possible(championship)

    def _round_name(self, team_count: int) -> str:
        labels = {
            2: "Final",
            4: "Semifinal",
            8: "Quartas de Final",
            16: "Oitavas de Final",
        }
        return labels.get(team_count, f"Rodada com {team_count} times")

    def _must_find_championship(self, championships: list[dict[str, Any]], championship_id: str) -> dict[str, Any]:
        for c in championships:
            if c["id"] == championship_id:
                return c
        raise ValueError("Campeonato não encontrado.")

    def _must_find_match(self, championship: dict[str, Any], match_id: str) -> dict[str, Any]:
        for m in championship["matches"]:
            if m["id"] == match_id:
                return m
        raise ValueError("Partida não encontrada.")