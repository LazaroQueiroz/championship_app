from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from app.storage import JsonRepository
from app.utils import ask_choice, ask_int, ask_non_empty
from app.services.player_service import PlayerService
from app.services.team_service import TeamService
from app.services.team_generator import generate_balanced_teams
from app.services.championship_service import ChampionshipService
from app.services.stats_service import StatsService


class ChampionshipCLI:
    def __init__(self, base_dir: Path):
        data_dir = base_dir / "data"
        self.player_service = PlayerService(JsonRepository(data_dir / "players.json", default=[]))
        self.team_service = TeamService(JsonRepository(data_dir / "teams.json", default=[]), self.player_service)
        self.championship_service = ChampionshipService(
            JsonRepository(data_dir / "championships.json", default=[]),
            self.team_service,
        )
        self.stats_service = StatsService(self.player_service, self.team_service)

    def run(self) -> None:
        while True:
            print("\n=== GERENCIADOR DE CAMPEONATOS ===")
            print("1) Jogadores (CRUD)")
            print("2) Times (CRUD)")
            print("3) Gerar times balanceados")
            print("4) Campeonatos")
            print("5) Estatísticas e histórico")
            print("0) Sair")
            choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "0"])

            if choice == "1":
                self.players_menu()
            elif choice == "2":
                self.teams_menu()
            elif choice == "3":
                self.balanced_teams_menu()
            elif choice == "4":
                self.championships_menu()
            elif choice == "5":
                self.stats_menu()
            else:
                print("Até mais!")
                return

    def players_menu(self) -> None:
        while True:
            print("\n--- Jogadores ---")
            print("1) Listar")
            print("2) Criar")
            print("3) Editar")
            print("4) Excluir")
            print("0) Voltar")
            choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])

            try:
                if choice == "1":
                    players = self.player_service.list_players()
                    if not players:
                        print("Nenhum jogador cadastrado.")
                    for p in players:
                        print(f"- {p['id']} | {p['name']} | {'★' * p['stars']}{'☆' * (5 - p['stars'])}")
                elif choice == "2":
                    name = ask_non_empty("Nome do jogador: ")
                    stars = ask_int("Estrelas (0-5): ", 0, 5)
                    created = self.player_service.create_player(name, stars)
                    print(f"Jogador criado: {created['id']}")
                elif choice == "3":
                    player_id = ask_non_empty("ID do jogador: ")
                    existing = self.player_service.get_player(player_id)
                    if not existing:
                        print("Jogador não encontrado.")
                        continue
                    name = ask_non_empty(f"Novo nome [{existing['name']}]: ")
                    stars = ask_int(f"Novas estrelas (0-5) [{existing['stars']}]: ", 0, 5)
                    self.player_service.update_player(player_id, name, stars)
                    print("Jogador atualizado.")
                elif choice == "4":
                    player_id = ask_non_empty("ID do jogador: ")
                    self.player_service.delete_player(player_id)
                    self.team_service.remove_player_from_all_teams(player_id)
                    print("Jogador excluído e removido dos times.")
                else:
                    return
            except ValueError as e:
                print(f"Erro: {e}")

    def teams_menu(self) -> None:
        while True:
            print("\n--- Times ---")
            print("1) Listar")
            print("2) Criar manualmente")
            print("3) Editar")
            print("4) Excluir")
            print("0) Voltar")
            choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])

            try:
                if choice == "1":
                    self._print_teams()
                elif choice == "2":
                    self.create_team_manually()
                elif choice == "3":
                    self.edit_team()
                elif choice == "4":
                    team_id = ask_non_empty("ID do time: ")
                    self.team_service.delete_team(team_id)
                    print("Time excluído.")
                else:
                    return
            except ValueError as e:
                print(f"Erro: {e}")

    def balanced_teams_menu(self) -> None:
        players = self.player_service.list_players()
        if len(players) < 2:
            print("Cadastre ao menos 2 jogadores antes.")
            return

        number_of_teams = ask_int("Quantos times balanceados gerar? ", 2, len(players))
        try:
            generated = generate_balanced_teams(players, number_of_teams)
        except ValueError as e:
            print(f"Erro: {e}")
            return

        print("\nPrévia dos times balanceados:")
        for t in generated:
            names = ", ".join(p["name"] for p in t["players"])
            print(f"Time #{t['slot']} | Total estrelas: {t['stars_total']} | Média: {t['stars_avg']} | {names}")

        save = ask_choice("Salvar como times oficiais? (s/n): ", ["s", "n"])
        if save == "n":
            return

        for t in generated:
            suggested = f"Time Balanceado {t['slot']}"
            name = input(f"Nome do time [{suggested}]: ").strip() or suggested
            player_ids = [p["id"] for p in t["players"]]
            try:
                self.team_service.create_team(name, player_ids)
                print(f"Time '{name}' criado.")
            except ValueError as e:
                print(f"Não foi possível criar '{name}': {e}")

    def championships_menu(self) -> None:
        while True:
            print("\n--- Campeonatos ---")
            print("1) Criar campeonato")
            print("2) Listar campeonatos")
            print("3) Gerenciar campeonato")
            print("0) Voltar")
            choice = ask_choice("Escolha: ", ["1", "2", "3", "0"])

            try:
                if choice == "1":
                    self.create_championship()
                elif choice == "2":
                    self.list_championships()
                elif choice == "3":
                    self.manage_championship()
                else:
                    return
            except ValueError as e:
                print(f"Erro: {e}")

    def create_championship(self) -> None:
        teams = self.team_service.list_teams()
        if len(teams) < 2:
            print("Cadastre ao menos 2 times antes.")
            return

        print("Times disponíveis:")
        for t in teams:
            print(f"- {t['id']} | {t['name']}")

        name = ask_non_empty("Nome do campeonato: ")
        ids_raw = ask_non_empty("IDs dos times participantes (separados por vírgula): ")
        team_ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
        group_count = ask_int("Número de grupos: ", 1, len(team_ids))
        duration = ask_int("Duração de cada partida (em minutos): ", 1)

        ch = self.championship_service.create_championship(name, team_ids, group_count, duration)
        print(f"Campeonato criado com ID: {ch['id']}")

    def list_championships(self) -> None:
        championships = self.championship_service.list_championships()
        if not championships:
            print("Nenhum campeonato cadastrado.")
            return

        for ch in championships:
            champion_name = "-"
            champion_id = ch.get("knockout", {}).get("champion_team_id")
            if champion_id:
                team = self.team_service.get_team(champion_id)
                champion_name = team["name"] if team else champion_id
            print(
                f"- {ch['id']} | {ch['name']} | Status: {ch['status']} | Criado: {ch['created_at']} | Campeão: {champion_name}"
            )

    def manage_championship(self) -> None:
        championship_id = ask_non_empty("ID do campeonato: ")
        ch = self.championship_service.get_championship(championship_id)
        if not ch:
            print("Campeonato não encontrado.")
            return

        while True:
            ch = self.championship_service.get_championship(championship_id)
            print(f"\n--- Gerenciar: {ch['name']} ({ch['status']}) ---")
            print("1) Ver grupos e tabela")
            print("2) Ver partidas")
            print("3) Registrar partida (timer em tempo real)")
            print("4) Gerar mata-mata")
            print("5) Ver chave mata-mata")
            print("0) Voltar")
            choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "0"])

            try:
                if choice == "1":
                    self.print_groups(ch)
                elif choice == "2":
                    self.print_matches(ch)
                elif choice == "3":
                    self.play_match(championship_id)
                elif choice == "4":
                    q = ask_int("Quantos times classificam por grupo? ", 1)
                    self.championship_service.create_knockout(championship_id, q)
                    print("Mata-mata gerado com sucesso.")
                elif choice == "5":
                    self.print_knockout_bracket(ch)
                else:
                    return
            except ValueError as e:
                print(f"Erro: {e}")

    def print_groups(self, championship: dict[str, Any]) -> None:
        for group in championship["groups"]:
            print(f"\nGrupo {group['name']}")
            print("Time | P | V | E | D | GP | GC | SG | Pts")
            rows = sorted(group["standings"].values(), key=lambda r: (-r["points"], -r["gd"], r["team_id"]))
            for r in rows:
                team = self.team_service.get_team(r["team_id"])
                team_name = team["name"] if team else r["team_id"]
                print(
                    f"{team_name} | {r['played']} | {r['wins']} | {r['draws']} | {r['losses']} | "
                    f"{r['gf']} | {r['ga']} | {r['gd']} | {r['points']}"
                )

    def print_matches(self, championship: dict[str, Any]) -> None:
        matches = sorted(championship["matches"], key=lambda m: m["schedule_order"])
        if not matches:
            print("Sem partidas.")
            return

        for m in matches:
            home_name = self._team_name(m["home_team_id"])
            away_name = self._team_name(m["away_team_id"])
            if m["is_played"]:
                score = f"{m['goals_home']} x {m['goals_away']}"
            else:
                score = "vs"
            grp = f"Grupo {m['group_name']}" if m["group_name"] else m.get("round_name", "-")
            print(
                f"[{m['schedule_order']:03d}] {m['id']} | {m['phase']} | {grp} | {home_name} {score} {away_name} | "
                f"{'JOGADA' if m['is_played'] else 'PENDENTE'}"
            )

    def play_match(self, championship_id: str) -> None:
        unplayed = self.championship_service.get_unplayed_matches(championship_id)
        if not unplayed:
            print("Não há partidas pendentes.")
            return

        print("Partidas pendentes:")
        for m in unplayed:
            print(
                f"- {m['id']} | Ordem {m['schedule_order']} | {self._team_name(m['home_team_id'])} x {self._team_name(m['away_team_id'])}"
            )
        match_id = ask_non_empty("ID da partida para iniciar: ")

        ch = self.championship_service.get_championship(championship_id)
        match = next((m for m in ch["matches"] if m["id"] == match_id), None)
        if not match:
            print("Partida não encontrada.")
            return
        if match["is_played"]:
            print("Partida já jogada.")
            return

        goals = self._run_live_match(ch, match)
        tie_winner = None
        if match["phase"] == "knockout":
            home_goals = sum(1 for g in goals if g["team_id"] == match["home_team_id"])
            away_goals = sum(1 for g in goals if g["team_id"] == match["away_team_id"])
            if home_goals == away_goals:
                print("Empate no mata-mata. Escolha vencedor no desempate:")
                print(f"1) {self._team_name(match['home_team_id'])}")
                print(f"2) {self._team_name(match['away_team_id'])}")
                selected = ask_choice("Vencedor: ", ["1", "2"])
                tie_winner = match["home_team_id"] if selected == "1" else match["away_team_id"]

        self.championship_service.record_match_result(championship_id, match_id, goals, tie_winner)
        print("Partida registrada com sucesso.")

    def print_knockout_bracket(self, championship: dict[str, Any]) -> None:
        rounds = championship.get("knockout", {}).get("rounds", [])
        if not rounds:
            print("Mata-mata ainda não gerado.")
            return

        print("\n=== CHAVE DO MATA-MATA ===")
        for rd in rounds:
            print(f"\n{rd['name']}")
            for mid in rd["match_ids"]:
                match = next(m for m in championship["matches"] if m["id"] == mid)
                home = self._team_name(match["home_team_id"])
                away = self._team_name(match["away_team_id"])
                if match["is_played"]:
                    extra = f"{match['goals_home']} x {match['goals_away']}"
                    if match.get("winner_team_id"):
                        extra += f" | Vencedor: {self._team_name(match['winner_team_id'])}"
                else:
                    extra = "vs"
                print(f"- {match['id']}: {home} {extra} {away}")

        champion_id = championship.get("knockout", {}).get("champion_team_id")
        if champion_id:
            print(f"\n🏆 Campeão: {self._team_name(champion_id)}")

    def stats_menu(self) -> None:
        championships = self.championship_service.list_championships()
        stats = self.stats_service.aggregate(championships)

        print("\n=== ESTATÍSTICAS GERAIS ===")
        print(f"Total de campeonatos: {stats['championship_count']}")

        if stats["best_player"]:
            best = stats["best_player"]
            print(f"Melhor jogador (mais gols): {best['player_name']} ({best['goals']} gols)")
        else:
            print("Melhor jogador: sem dados ainda.")

        print("\nTop jogadores:")
        if not stats["top_players"]:
            print("- Sem gols registrados.")
        else:
            for p in stats["top_players"][:10]:
                print(f"- {p['player_name']}: {p['goals']} gols")

        print("\nTimes com mais títulos:")
        if not stats["top_teams_by_titles"]:
            print("- Sem campeões definidos ainda.")
        else:
            for t in stats["top_teams_by_titles"]:
                print(f"- {t['team_name']}: {t['titles']} título(s)")

        print("\nGols por fase:")
        if not stats["goals_by_phase"]:
            print("- Sem partidas jogadas ainda.")
        else:
            for phase, goals in stats["goals_by_phase"].items():
                print(f"- {phase}: {goals}")

        print("\nTendência histórica (gols por campeonato):")
        if not stats["historical_trend"]:
            print("- Sem histórico.")
        else:
            for row in stats["historical_trend"]:
                delta = row["delta_vs_previous"]
                delta_label = "N/A" if delta is None else (f"+{delta}" if delta >= 0 else str(delta))
                print(f"- {row['name']} ({row['created_at']}): {row['total_goals']} gols | Δ {delta_label}")

    def _run_live_match(self, championship: dict[str, Any], match: dict[str, Any]) -> list[dict[str, Any]]:
        duration_seconds = match["duration_minutes"] * 60
        remaining = {"seconds": duration_seconds}
        stop_event = threading.Event()
        time_up_event = threading.Event()

        home_team = self.team_service.get_team(match["home_team_id"])
        away_team = self.team_service.get_team(match["away_team_id"])

        home_score = 0
        away_score = 0
        goals_by_player: list[dict[str, Any]] = []

        def timer_thread() -> None:
            while remaining["seconds"] > 0 and not stop_event.is_set():
                mins = remaining["seconds"] // 60
                secs = remaining["seconds"] % 60
                print(f"\r⏱️  Tempo restante: {mins:02d}:{secs:02d}", end="", flush=True)
                time.sleep(1)
                remaining["seconds"] -= 1

            if not stop_event.is_set():
                time_up_event.set()
                print("\nTempo encerrado!")

        t = threading.Thread(target=timer_thread, daemon=True)
        t.start()

        print(
            f"\nPartida iniciada: {home_team['name']} x {away_team['name']} | "
            f"Duração: {match['duration_minutes']} minuto(s)."
        )
        print("Comandos: gol, placar, fim")

        while not time_up_event.is_set():
            cmd = input("\nComando: ").strip().lower()
            if cmd == "gol":
                team_opt = ask_choice(
                    f"Time do gol (1={home_team['name']}, 2={away_team['name']}): ",
                    ["1", "2"],
                )
                scoring_team = home_team if team_opt == "1" else away_team
                players = scoring_team["player_ids"]
                if not players:
                    print("Este time não possui jogadores cadastrados para marcar gol.")
                    continue

                print("Jogadores disponíveis:")
                for idx, pid in enumerate(players, start=1):
                    p = self.player_service.get_player(pid)
                    print(f"{idx}) {p['name'] if p else pid}")

                selected_index = ask_int("Número do jogador: ", 1, len(players))
                player_id = players[selected_index - 1]
                elapsed = duration_seconds - remaining["seconds"]
                minute = max(1, (elapsed // 60) + 1)

                if scoring_team["id"] == home_team["id"]:
                    home_score += 1
                else:
                    away_score += 1

                goals_by_player.append(
                    {
                        "player_id": player_id,
                        "team_id": scoring_team["id"],
                        "minute": minute,
                    }
                )
                print(f"Gol registrado! Placar: {home_team['name']} {home_score} x {away_score} {away_team['name']}")

            elif cmd == "placar":
                print(f"Placar atual: {home_team['name']} {home_score} x {away_score} {away_team['name']}")
            elif cmd == "fim":
                confirm = ask_choice("Encerrar partida agora? (s/n): ", ["s", "n"])
                if confirm == "s":
                    stop_event.set()
                    break
            else:
                print("Comando inválido. Use: gol, placar, fim")

        stop_event.set()
        t.join(timeout=1)
        print(f"Placar final: {home_team['name']} {home_score} x {away_score} {away_team['name']}")
        return goals_by_player

    def create_team_manually(self) -> None:
        players = self.player_service.list_players()
        if not players:
            print("Cadastre jogadores antes de criar times.")
            return

        print("Jogadores disponíveis:")
        for p in players:
            print(f"- {p['id']} | {p['name']} | {p['stars']}★")

        name = ask_non_empty("Nome do time: ")
        ids_raw = ask_non_empty("IDs dos jogadores (separados por vírgula): ")
        player_ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
        team = self.team_service.create_team(name, player_ids)
        print(f"Time criado: {team['id']}")

    def edit_team(self) -> None:
        team_id = ask_non_empty("ID do time: ")
        team = self.team_service.get_team(team_id)
        if not team:
            print("Time não encontrado.")
            return

        self._print_team(team)
        name = ask_non_empty(f"Novo nome [{team['name']}]: ")

        players = self.player_service.list_players()
        print("Jogadores disponíveis:")
        for p in players:
            print(f"- {p['id']} | {p['name']}")
        ids_raw = ask_non_empty("Novos IDs de jogadores (separados por vírgula): ")
        player_ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
        self.team_service.update_team(team_id, name, player_ids)
        print("Time atualizado.")

    def _print_teams(self) -> None:
        teams = self.team_service.list_teams()
        if not teams:
            print("Nenhum time cadastrado.")
            return
        for t in teams:
            self._print_team(t)

    def _print_team(self, team: dict[str, Any]) -> None:
        names = []
        for pid in team["player_ids"]:
            player = self.player_service.get_player(pid)
            names.append(player["name"] if player else pid)
        print(f"- {team['id']} | {team['name']} | Jogadores: {', '.join(names) if names else '(nenhum)'}")

    def _team_name(self, team_id: str | None) -> str:
        if not team_id:
            return "BYE"
        team = self.team_service.get_team(team_id)
        return team["name"] if team else team_id
