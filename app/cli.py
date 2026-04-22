from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

from app.storage import JsonRepository
from app.utils import ask_choice, ask_int, ask_non_empty, clear_screen, pause_screen, ask_index, ask_multi_index, GoBackError, handle_input
from app.services.player_service import PlayerService
from app.services.team_service import TeamService
from app.services.team_generator import generate_balanced_teams
from app.services.championship_service import ChampionshipService
from app.services.stats_service import StatsService
from app.ui import Colors, print_header, print_success, print_error, print_warning, print_info, format_table


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
        from app.ui import Colors, print_header
        while True:
            clear_screen()
            print_header("Gerenciador de Campeonatos", color=Colors.B_BLUE)
            print(f"{Colors.CYAN}1){Colors.RESET} Jogadores (CRUD)")
            print(f"{Colors.CYAN}2){Colors.RESET} Times (CRUD)")
            print(f"{Colors.CYAN}3){Colors.RESET} Gerar times balanceados (Draft)")
            print(f"{Colors.CYAN}4){Colors.RESET} Campeonatos")
            print(f"{Colors.CYAN}5){Colors.RESET} Estatísticas e histórico")
            print(f"{Colors.RED}0){Colors.RESET} Sair")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "0"])
            except GoBackError:
                return

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
                pause_screen()
            else:
                print("Até mais!")
                return

    def players_menu(self) -> None:
        from app.ui import Colors, print_header
        while True:
            clear_screen()
            print_header("Jogadores", color=Colors.CYAN)
            print(f"{Colors.CYAN}1){Colors.RESET} Listar")
            print(f"{Colors.CYAN}2){Colors.RESET} Criar")
            print(f"{Colors.CYAN}3){Colors.RESET} Editar")
            print(f"{Colors.CYAN}4){Colors.RESET} Excluir")
            print(f"{Colors.RED}0){Colors.RESET} Voltar")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])
            except GoBackError:
                return

            try:
                if choice == "1":
                    players = self.player_service.list_players()
                    if not players:
                        print_warning("Nenhum jogador cadastrado.")
                    else:
                        print_header("Lista de Jogadores", color=Colors.CYAN)
                        rows = [[str(i), p['name'], '★' * p['stars'] + '☆' * (5 - p['stars'])] for i, p in enumerate(players, 1)]
                        format_table(["#", "Nome", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])
                    pause_screen()
                elif choice == "2":
                    state = 0
                    player_name = ""
                    while True:
                        try:
                            if state == 0:
                                player_name = ask_non_empty("Nome do jogador: ")
                                state += 1
                            elif state == 1:
                                stars = ask_int("Estrelas (0-5): ", 0, 5)
                                self.player_service.create_player(player_name, stars)
                                print_success(f"Jogador '{player_name}' criado.")
                                break
                        except GoBackError:
                            if state == 0: break
                            state -= 1
                elif choice == "3":
                    players = self.player_service.list_players()
                    if not players:
                        print("Nenhum jogador para editar.")
                        continue
                    state = 0
                    while True:
                        try:
                            if state == 0:
                                for idx, p in enumerate(players, start=1):
                                    print(f"{idx}) {p['name']} | {'★' * p['stars']}{'☆' * (5 - p['stars'])}")
                                sel = ask_index("Número do jogador (0 para cancelar): ", len(players), allow_cancel=True)
                                if sel is None:
                                    break
                                existing = players[sel - 1]
                                player_id = existing['id']
                                state += 1
                            elif state == 1:
                                name = ask_non_empty(f"Novo nome [{existing['name']}]: ")
                                state += 1
                            elif state == 2:
                                stars = ask_int(f"Novas estrelas (0-5) [{existing['stars']}]: ", 0, 5)
                                self.player_service.update_player(player_id, name, stars)
                                print("Jogador atualizado.")
                                break
                        except GoBackError:
                            if state == 0: break
                            state -= 1
                elif choice == "4":
                    players = self.player_service.list_players()
                    if not players:
                        print_warning("Nenhum jogador para excluir.")
                        continue
                    rows = [[str(i), p['name'], '★'*p['stars']+'☆'*(5-p['stars'])] for i, p in enumerate(players, 1)]
                    format_table(["#", "Nome", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])
                    try:
                        sel = ask_index("Número do jogador (0 para cancelar): ", len(players), allow_cancel=True)
                    except GoBackError:
                        continue
                    if sel is not None:
                        target = players[sel - 1]
                        try:
                            confirm = ask_choice(f"Confirmar exclusão de '{target['name']}'? (s/n): ", ["s", "n"])
                        except GoBackError:
                            continue
                        if confirm == "s":
                            self.player_service.delete_player(target['id'])
                            self.team_service.remove_player_from_all_teams(target['id'])
                            print_success("Jogador excluído e removido dos times.")
                else:
                    return
            except GoBackError:
                continue
            except ValueError as e:
                print(f"Erro: {e}")

    def teams_menu(self) -> None:
        from app.ui import Colors, print_header
        while True:
            clear_screen()
            print_header("Times", color=Colors.CYAN)
            print(f"{Colors.CYAN}1){Colors.RESET} Listar")
            print(f"{Colors.CYAN}2){Colors.RESET} Criar manualmente")
            print(f"{Colors.CYAN}3){Colors.RESET} Editar")
            print(f"{Colors.CYAN}4){Colors.RESET} Excluir")
            print(f"{Colors.RED}0){Colors.RESET} Voltar")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])
            except GoBackError:
                return

            try:
                if choice == "1":
                    self._print_teams()
                    pause_screen()
                elif choice == "2":
                    self.create_team_manually()
                    pause_screen()
                elif choice == "3":
                    self.edit_team()
                    pause_screen()
                elif choice == "4":
                    teams = self.team_service.list_teams()
                    if not teams:
                        print_warning("Nenhum time para excluir.")
                        continue
                    rows = [[str(i), t['name']] for i, t in enumerate(teams, 1)]
                    format_table(["#", "Time"], rows, [Colors.B_BLACK, Colors.B_WHITE])
                    try:
                        sel = ask_index("Número do time (0 para cancelar): ", len(teams), allow_cancel=True)
                    except GoBackError:
                        continue
                    if sel is not None:
                        target = teams[sel - 1]
                        try:
                            confirm = ask_choice(f"Confirmar exclusão de '{target['name']}'? (s/n): ", ["s", "n"])
                        except GoBackError:
                            continue
                        if confirm == "s":
                            self.team_service.delete_team(target['id'])
                            print_success("Time excluído.")
                else:
                    return
            except GoBackError:
                continue
            except ValueError as e:
                print(f"Erro: {e}")

    def balanced_teams_menu(self) -> None:
        players = self.player_service.list_players()
        if len(players) < 2:
            print("Cadastre ao menos 2 jogadores antes.")
            return

        state = 0
        number_of_teams = 0
        active_players = []
        generated = []
        
        while True:
            try:
                if state == 0:
                    clear_screen()
                    print("\nTodos os jogadores:")
                    for idx, p in enumerate(players, start=1):
                        print(f"{idx}) {p['name']} | {'★' * p['stars']}{'☆' * (5 - p['stars'])}")
                        
                    absent_indices = ask_multi_index("\nNúmeros dos jogadores AUSENTES (separados por vírgula, Enter para NENHUM): ", len(players), allow_empty=True)
                    absent_ids = [players[i-1]['id'] for i in absent_indices]
                    active_players = [p for p in players if p['id'] not in absent_ids]
                    
                    if len(active_players) < 2:
                        print("É necessário pelo menos 2 jogadores presentes.")
                        raise GoBackError()
                    
                    state += 1
                elif state == 1:
                    number_of_teams = ask_int("Quantos times balanceados gerar? (0 para cancelar): ", 0, len(active_players))
                    if number_of_teams == 0:
                        return
                    
                    try:
                        generated = generate_balanced_teams(active_players, number_of_teams)
                    except ValueError as e:
                        print(f"Erro: {e}")
                        continue
                        
                    print("\nPrévia dos times balanceados:")
                    for t in generated:
                        names = ", ".join(p["name"] for p in t["players"])
                        print(f"Time #{t['slot']} | Total estrelas: {t['stars_total']} | Média: {t['stars_avg']} | {names}")
                    state += 1
                elif state == 1:
                    save = ask_choice("Salvar como times oficiais? (s/n): ", ["s", "n"])
                    if save == "n":
                        return
                    state += 1
                elif state == 2:
                    for idx, t in enumerate(generated):
                        suggested = f"Time Balanceado {t['slot']}"
                        name = handle_input(f"Nome do time {idx+1}/{len(generated)} [{suggested}]: ").strip() or suggested
                        player_ids = [p["id"] for p in t["players"]]
                        try:
                            self.team_service.create_team(name, player_ids)
                            print(f"Time '{name}' criado.")
                        except ValueError as e:
                            print(f"Não foi possível criar '{name}': {e}")
                    break
            except GoBackError:
                if state == 0: break
                state -= 1

    def championships_menu(self) -> None:
        from app.ui import Colors, print_header
        while True:
            clear_screen()
            print_header("Campeonatos", color=Colors.CYAN)
            print(f"{Colors.CYAN}1){Colors.RESET} Criar campeonato")
            print(f"{Colors.CYAN}2){Colors.RESET} Listar campeonatos")
            print(f"{Colors.CYAN}3){Colors.RESET} Gerenciar campeonato")
            print(f"{Colors.CYAN}4){Colors.RESET} Excluir campeonato")
            print(f"{Colors.RED}0){Colors.RESET} Voltar")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])
            except GoBackError:
                return

            try:
                if choice == "1":
                    self.create_championship()
                elif choice == "2":
                    self.list_championships()
                    pause_screen()
                elif choice == "3":
                    self.manage_championship()
                elif choice == "4":
                    self.list_championships()
                    champs = self.championship_service.list_championships()
                    if champs:
                        try:
                            sel = ask_index("\nNúmero do campeonato para excluir (0 cancelar): ", len(champs), allow_cancel=True)
                        except GoBackError:
                            continue
                        if sel is not None:
                            target = champs[sel - 1]
                            try:
                                confirm = ask_choice(f"Confirmar exclusão de '{target['name']}'? (s/n): ", ["s", "n"])
                            except GoBackError:
                                continue
                            if confirm == "s":
                                self.championship_service.delete_championship(target['id'])
                                print_success("Campeonato apagado.")
                else:
                    return
            except GoBackError:
                continue
            except ValueError as e:
                print(f"Erro: {e}")

    def create_championship(self) -> None:
        from app.services.team_generator import COLORS

        state = 0
        name = ""
        opt = ""
        team_ids: list[str] = []
        group_count = 1
        duration = 1
        # We need a placeholder championship ID before actual save so teams
        # can reference it.  We generate it here and pass it along.
        import uuid
        pending_ch_id: str = ""

        while True:
            try:
                if state == 0:
                    name = ask_non_empty("Nome do campeonato: ")
                    state += 1

                elif state == 1:
                    clear_screen()
                    print_header(f"Criar Campeonato — {name}", color=Colors.B_BLUE)
                    print(f"{Colors.CYAN}1){Colors.RESET} Montar times manualmente (escolher jogadores por cor)")
                    print(f"{Colors.CYAN}2){Colors.RESET} Sorteio automático equilibrado")
                    print(f"{Colors.RED}0){Colors.RESET} Cancelar")
                    opt = ask_choice("Escolha: ", ["1", "2", "0"])
                    if opt == "0":
                        raise GoBackError()
                    state += 1

                elif state == 2:
                    all_players = self.player_service.list_players()
                    if not all_players:
                        print_error("Nenhum jogador cadastrado.")
                        raise GoBackError()

                    team_ids = []
                    # We need a stable placeholder ID for teams before the championship exists.
                    pending_ch_id = f"pending-{uuid.uuid4().hex[:8]}"

                    if opt == "1":
                        # Manual team creation with color names
                        qty_teams = ask_int("Quantos times? (mínimo 2): ", 2, len(all_players))
                        available_players = list(all_players)

                        for slot in range(qty_teams):
                            color = COLORS[slot % len(COLORS)]
                            if slot >= len(COLORS):
                                color = f"{color} {slot + 1}"
                            t_name = f"Time {color}"

                            clear_screen()
                            print_header(f"Montando {t_name}", color=Colors.CYAN)
                            if not available_players:
                                print_warning("Sem jogadores restantes.")
                                break

                            rows = [[str(i), p['name'], '★'*p['stars']+'☆'*(5-p['stars'])] for i, p in enumerate(available_players, 1)]
                            format_table(["#", "Jogador", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])

                            p_indices = ask_multi_index(f"\nJogadores do {t_name} (números CSV): ", len(available_players))
                            selected_ids = [available_players[i - 1]["id"] for i in p_indices]
                            # Remove from pool
                            available_players = [p for p in available_players if p["id"] not in selected_ids]
                            t_model = self.team_service.create_team(t_name, selected_ids, is_draft=True, championship_id=pending_ch_id)
                            team_ids.append(t_model["id"])

                    else:
                        # Auto balanced draft
                        clear_screen()
                        print_header("Sorteio Automático", color=Colors.CYAN)
                        rows = [[str(i), p['name'], '★'*p['stars']+'☆'*(5-p['stars'])] for i, p in enumerate(all_players, 1)]
                        format_table(["#", "Jogador", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])

                        absent_indices = ask_multi_index("\nAusentes (números CSV, Enter p/ nenhum): ", len(all_players), allow_empty=True)
                        absent_ids = {all_players[i-1]['id'] for i in absent_indices}
                        active_players = [p for p in all_players if p['id'] not in absent_ids]

                        qty_teams = ask_int("\nQuantos times sortear? (mínimo 2): ", 2, len(active_players))
                        generated = generate_balanced_teams(active_players, qty_teams)

                        print_header("Prévia dos Times Sorteados", color=Colors.B_GREEN)
                        for t in generated:
                            names = ", ".join(p["name"] for p in t["players"])
                            print(f"  {Colors.BOLD}{t['name']}{Colors.RESET}  ★ total={t['stars_total']} média={t['stars_avg']}")
                            print(f"    {Colors.B_BLACK}{names}{Colors.RESET}")

                        confirm = ask_choice("\nConfirmar sorteio? (s/n): ", ["s", "n"])
                        if confirm == "n":
                            continue

                        for t in generated:
                            p_ids = [p["id"] for p in t["players"]]
                            t_model = self.team_service.create_team(t["name"], p_ids, is_draft=True, championship_id=pending_ch_id)
                            team_ids.append(t_model["id"])

                    if len(team_ids) < 2:
                        print_error("São necessários ao menos 2 times.")
                        # Clean up any already-created teams
                        for tid in team_ids:
                            try: self.team_service.delete_team(tid)
                            except: pass
                        team_ids = []
                        state -= 1
                        continue
                    state += 1

                elif state == 3:
                    group_count = ask_int("\nNúmero de grupos: ", 1, len(team_ids))
                    state += 1

                elif state == 4:
                    duration = ask_int("Duração de cada partida (em minutos): ", 1)
                    ch = self.championship_service.create_championship(name, team_ids, group_count, duration)
                    # Patch all pending teams to use the real championship ID
                    for tid in team_ids:
                        t = self.team_service.get_team(tid)
                        if t and t.get("championship_id") == pending_ch_id:
                            all_teams = self.team_service._load()
                            for stored in all_teams:
                                if stored["id"] == tid:
                                    stored["championship_id"] = ch["id"]
                            self.team_service._save(all_teams)
                    print_success(f"Campeonato '{name}' criado com sucesso!")
                    break

            except GoBackError:
                if state == 0:
                    # Clean up any teams created so far
                    for tid in team_ids:
                        try: self.team_service.delete_team(tid)
                        except: pass
                    break
                state -= 1

    def list_championships(self) -> None:
        championships = self.championship_service.list_championships()
        if not championships:
            print_warning("Nenhum campeonato cadastrado.")
            return

        print_header("Campeonatos", color=Colors.B_YELLOW)
        status_map = {
            "group_stage": "Fase de Grupos",
            "group_finished": "Grupos Encerrados",
            "knockout": "Mata-Mata",
            "finished": "🏆 Finalizado",
        }
        rows = []
        for idx, ch in enumerate(championships, start=1):
            champion_name = "-"
            champion_id = ch.get("knockout", {}).get("champion_team_id")
            if champion_id:
                # get_team searches all teams including archived
                all_teams = self.team_service._load()
                t = next((t for t in all_teams if t["id"] == champion_id), None)
                champion_name = t["name"] if t else champion_id
            status = status_map.get(ch['status'], ch['status'])
            date = (ch.get('created_at') or "")[:10]
            rows.append([str(idx), ch['name'], status, date, champion_name])
        format_table(
            ["#", "Nome", "Status", "Data", "Campeão"],
            rows,
            [Colors.B_BLACK, Colors.B_WHITE, Colors.CYAN, Colors.B_BLACK, Colors.B_YELLOW]
        )

    def manage_championship(self) -> None:
        champs = self.championship_service.list_championships()
        if not champs:
            print("Nenhum campeonato encontrado.")
            return
        self.list_championships()
        try:
            sel = ask_index("Número do campeonato (0 para cancelar): ", len(champs), allow_cancel=True)
            if sel is None:
                return
            championship_id = champs[sel - 1]['id']
        except GoBackError:
            return
        ch = self.championship_service.get_championship(championship_id)
        if not ch:
            print("Campeonato não encontrado.")
            return

        while True:
            clear_screen()
            ch = self.championship_service.get_championship(championship_id)
            if not ch:
                print_error("Campeonato não encontrado (pode ter sido excluído).")
                return
            status_label = ch['status'].upper()
            print_header(f"{ch['name']}  [{status_label}]", color=Colors.B_YELLOW)
            print(f"{Colors.CYAN}1){Colors.RESET} Ver grupos e tabela")
            print(f"{Colors.CYAN}2){Colors.RESET} Ver partidas")
            print(f"{Colors.CYAN}3){Colors.RESET} Registrar partida (timer em tempo real)")
            print(f"{Colors.CYAN}4){Colors.RESET} Gerar mata-mata")
            print(f"{Colors.CYAN}5){Colors.RESET} Ver chave mata-mata")
            print(f"{Colors.CYAN}6){Colors.RESET} Ver detalhes de uma partida")
            print(f"{Colors.CYAN}7){Colors.RESET} Editar resultado de partida")
            print(f"{Colors.RED}0){Colors.RESET} Voltar")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "6", "7", "0"])
            except GoBackError:
                return

            try:
                if choice == "1":
                    self.print_groups(ch)
                    pause_screen()
                elif choice == "2":
                    self.print_matches(ch)
                    pause_screen()
                elif choice == "3":
                    self.play_match(championship_id)
                elif choice == "4":
                    try:
                        q = ask_int("Quantos times classificam por grupo? ", 1)
                    except GoBackError:
                        continue
                    self.championship_service.create_knockout(championship_id, q)
                    print("Mata-mata gerado com sucesso.")
                    ch_after = self.championship_service.get_championship(championship_id)
                    if ch_after and "knockout" in ch_after and ch_after["knockout"].get("rounds"):
                        first_round = ch_after["knockout"]["rounds"][0]
                        duration = ask_int(f"\nDuração de cada partida da {first_round['name']} (em minutos): ", 1)
                        self.championship_service.update_round_duration(championship_id, first_round["name"], duration)
                elif choice == "5":
                    self.print_knockout_bracket(ch)
                    pause_screen()
                elif choice == "6":
                    self.view_match_details(ch)
                    pause_screen()
                elif choice == "7":
                    self.edit_match_result(championship_id, ch)
                else:
                    return
            except GoBackError:
                continue
            except ValueError as e:
                print(f"Erro: {e}")

    def print_groups(self, championship: dict[str, Any]) -> None:
        print_header(f"Grupos — {championship['name']}", color=Colors.B_BLUE)
        for group in championship["groups"]:
            print(f"{Colors.BOLD}{Colors.YELLOW}  ▶ Grupo {group['name']}{Colors.RESET}")
            standings = sorted(group["standings"].values(), key=lambda r: (-r["points"], -r["gd"], r["team_id"]))
            table_rows = []
            for pos, r in enumerate(standings, 1):
                team = self.team_service.get_team(r["team_id"])
                t_name = team["name"] if team else r["team_id"]
                table_rows.append([
                    str(pos), t_name,
                    str(r["played"]), str(r["wins"]), str(r["draws"]), str(r["losses"]),
                    str(r["gf"]), str(r["ga"]), str(r["gd"]), str(r["points"])
                ])
            format_table(
                ["#", "Time", "P", "V", "E", "D", "GP", "GC", "SG", "Pts"],
                table_rows,
                [Colors.B_BLACK, Colors.B_WHITE, None, Colors.B_GREEN, Colors.B_YELLOW, Colors.B_RED, None, None, None, Colors.CYAN]
            )
            print()

    def print_matches(self, championship: dict[str, Any]) -> None:
        matches = sorted(championship["matches"], key=lambda m: m["schedule_order"])
        if not matches:
            print_warning("Sem partidas.")
            return

        print_header(f"Partidas — {championship['name']}", color=Colors.B_BLUE)
        rows = []
        for idx, m in enumerate(matches, start=1):
            home_name = self._team_name(m["home_team_id"])
            away_name = self._team_name(m["away_team_id"])
            if m["is_played"]:
                score = f"{m['goals_home']} x {m['goals_away']}"
                if m.get("penalties_home") is not None:
                    score += f" ({m['penalties_home']}x{m['penalties_away']})"
                status = "✅"
            else:
                score = "vs"
                status = "⏳"
            grp = f"Grupo {m['group_name']}" if m["group_name"] else m.get("round_name", "-")
            rows.append([str(idx), status, grp, home_name, score, away_name])
        format_table(
            ["#", "St", "Fase", "Casa", "Placar", "Fora"],
            rows,
            [Colors.B_BLACK, None, Colors.MAGENTA, Colors.B_WHITE, Colors.B_YELLOW, Colors.B_WHITE]
        )

    def _run_penalty_shootout(self, home_team: dict[str, Any], away_team: dict[str, Any]) -> tuple[int, int, list[dict[str, Any]]]:
        print_header(f"⚽ Disputa de Pênaltis", color=Colors.B_RED)
        print(f"  {Colors.BOLD}{home_team['name']}{Colors.RESET} vs {Colors.BOLD}{away_team['name']}{Colors.RESET}")
        print(f"  {Colors.B_BLACK}Comandos: batida, desfazer, terminar{Colors.RESET}")
        penalties_home = 0
        penalties_away = 0
        penalties_by_player: list[dict[str, Any]] = []

        while True:
            print(f"\nPlacar Pênaltis: {home_team['name']} {penalties_home} x {penalties_away} {away_team['name']} | Cobranças: {len(penalties_by_player)}")
            try:
                cmd = handle_input("Comando (batida/desfazer/terminar): ").strip().lower()
            except GoBackError:
                continue

            if cmd == "batida":
                try:
                    team_opt = ask_choice(
                        f"Time (1={home_team['name']}, 2={away_team['name']}, 0=Cancelar): ",
                        ["1", "2", "0"],
                    )
                    if team_opt == "0":
                        continue
                    scoring_team = home_team if team_opt == "1" else away_team
                    players = scoring_team["player_ids"]
                    if not players:
                        print("Time sem jogadores.")
                        continue

                    print("Jogadores:")
                    for idx, pid in enumerate(players, start=1):
                        p = self.player_service.get_player(pid)
                        print(f"  {idx}) {p['name'] if p else pid}")

                    pidx = ask_index("Número do jogador (0 cancelar): ", len(players), allow_cancel=True)
                    if pidx is None:
                        continue
                    player_id = players[pidx - 1]

                    res = ask_choice("Resultado (1=Gol, 2=Perdeu, 0=Cancelar): ", ["1", "2", "0"])
                    if res == "0":
                        continue
                    
                    cored = (res == "1")

                    penalties_by_player.append({
                        "player_id": player_id,
                        "team_id": scoring_team["id"],
                        "scored": cored,
                    })
                    
                    if cored:
                        if scoring_team["id"] == home_team["id"]:
                            penalties_home += 1
                        else:
                            penalties_away += 1
                    print("Cobrança registrada.")
                except GoBackError:
                    continue

            elif cmd == "desfazer":
                if not penalties_by_player:
                    print("Nenhuma cobrança para desfazer.")
                else:
                    last = penalties_by_player.pop()
                    if last["scored"]:
                        if last["team_id"] == home_team["id"]:
                            penalties_home -= 1
                        else:
                            penalties_away -= 1
                    print("Última cobrança removida.")

            elif cmd == "terminar":
                if penalties_home == penalties_away:
                    print("Pênaltis não podem estar empatados.")
                    continue
                return penalties_home, penalties_away, penalties_by_player
            else:
                print("Comando inválido. Use: batida, desfazer, terminar")

    def play_match(self, championship_id: str) -> None:
        unplayed = self.championship_service.get_unplayed_matches(championship_id)
        if not unplayed:
            print("Não há partidas pendentes.")
            return

        print("Partidas pendentes:")
        for idx, m in enumerate(unplayed, start=1):
            print(
                f"{idx}) Ordem {m['schedule_order']} | {self._team_name(m['home_team_id'])} x {self._team_name(m['away_team_id'])}"
            )
        try:
            sel = ask_index("Número da partida para iniciar (0 cancelar): ", len(unplayed), allow_cancel=True)
        except GoBackError:
            return
        if sel is None:
            return

        ch = self.championship_service.get_championship(championship_id)
        match = unplayed[sel - 1]
        match_id = match['id']
 

        goals = self._run_live_match(ch, match)
        penalties_home, penalties_away = None, None
        penalties_by_player = None
        if match["phase"] == "knockout":
            home_goals = sum(1 for g in goals if g["team_id"] == match["home_team_id"])
            away_goals = sum(1 for g in goals if g["team_id"] == match["away_team_id"])
            if home_goals == away_goals:
                h_team = self.team_service.get_team(match["home_team_id"])
                a_team = self.team_service.get_team(match["away_team_id"])
                if h_team and a_team:
                    penalties_home, penalties_away, penalties_by_player = self._run_penalty_shootout(h_team, a_team)
                else:
                    print("Erro: times não encontrados para disputa de pênaltis.")
                    penalties_home, penalties_away, penalties_by_player = 0, 0, []

        ch_before = self.championship_service.get_championship(championship_id)
        rounds_before = len(ch_before.get("knockout", {}).get("rounds", [])) if ch_before and ch_before.get("knockout") else 0

        self.championship_service.record_match_result(
            championship_id, match_id, goals, penalties_home=penalties_home, penalties_away=penalties_away, penalties_by_player=penalties_by_player
        )
        
        ch_after = self.championship_service.get_championship(championship_id)
        rounds_after = len(ch_after.get("knockout", {}).get("rounds", [])) if ch_after and ch_after.get("knockout") else 0
        
        if rounds_after > rounds_before:
            new_round = ch_after["knockout"]["rounds"][-1]
            print(f"\n🏆 Nova fase gerada: {new_round['name']}")
            dur = ask_int(f"Duração de cada partida da {new_round['name']} (em minutos): ", 1)
            self.championship_service.update_round_duration(championship_id, new_round["name"], dur)
            
        print("Partida registrada com sucesso.")

    def print_knockout_bracket(self, championship: dict[str, Any]) -> None:
        rounds = championship.get("knockout", {}).get("rounds", [])
        if not rounds:
            print("Mata-mata ainda não gerado.")
            return

        print_header(f"Chave do Mata-Mata — {championship['name']}", color=Colors.B_YELLOW)
        for rd in rounds:
            print(f"  {Colors.BOLD}{Colors.YELLOW}{rd['name']}{Colors.RESET}")
            for mid in rd["match_ids"]:
                match = next(m for m in championship["matches"] if m["id"] == mid)
                home = self._team_name(match["home_team_id"])
                away = self._team_name(match["away_team_id"])
                if match["is_played"]:
                    goal_str = f"{match['goals_home']} x {match['goals_away']}"
                    if match.get("penalties_home") is not None:
                        goal_str += f" ({match['penalties_home']}x{match['penalties_away']})"
                    winner_str = ""
                    if match.get("winner_team_id"):
                        winner_str = f"  {Colors.B_GREEN}→ {self._team_name(match['winner_team_id'])}{Colors.RESET}"
                    print(f"  {Colors.B_BLACK}•{Colors.RESET} {Colors.B_WHITE}{home}{Colors.RESET}  {Colors.B_YELLOW}{goal_str}{Colors.RESET}  {Colors.B_WHITE}{away}{Colors.RESET}{winner_str}")
                else:
                    print(f"  {Colors.B_BLACK}•{Colors.RESET} {home}  {Colors.DIM}vs{Colors.RESET}  {away}")
            print()

        champion_id = championship.get("knockout", {}).get("champion_team_id")
        if champion_id:
            print(f"  {Colors.B_YELLOW}🏆  CAMPEÃO: {Colors.BOLD}{self._team_name(champion_id)}{Colors.RESET}")

    def view_match_details(self, championship: dict[str, Any]) -> None:
        matches = sorted(championship["matches"], key=lambda m: m["schedule_order"])
        if not matches:
            print("Sem partidas.")
            return

        self.print_matches(championship)
        try:
            sel = ask_index("\nNúmero da partida para ver detalhes (0 cancelar): ", len(matches), allow_cancel=True)
        except GoBackError:
            return
        if sel is None:
            return

        m = matches[sel - 1]
        home_name = self._team_name(m["home_team_id"])
        away_name = self._team_name(m["away_team_id"])

        clear_screen()
        grp = f"Grupo {m['group_name']}" if m["group_name"] else m.get("round_name", "-")
        print_header("Detalhes da Partida", color=Colors.B_BLUE)

        info_rows = [
            ["Fase", f"{m['phase'].upper()} — {grp}"],
            ["Duração", f"{m.get('duration_minutes', '?')} min"],
            ["Status", "JOGADA ✅" if m['is_played'] else "PENDENTE ⏳"],
        ]
        if m.get("played_at"):
            info_rows.append(["Jogada em", m['played_at']])
        format_table(["Campo", "Valor"], info_rows, [Colors.B_BLACK, Colors.B_WHITE])
        print()

        if m["is_played"]:
            score_str = f"{m['goals_home']}  x  {m['goals_away']}"
            if m.get("penalties_home") is not None:
                score_str += f"  (Pênaltis: {m['penalties_home']} x {m['penalties_away']})"
            print(f"  {Colors.BOLD}{Colors.B_WHITE}{home_name}{Colors.RESET}  {Colors.B_YELLOW}{score_str}{Colors.RESET}  {Colors.BOLD}{Colors.B_WHITE}{away_name}{Colors.RESET}")
        else:
            print(f"  {Colors.B_WHITE}{home_name}{Colors.RESET}  {Colors.DIM}vs{Colors.RESET}  {Colors.B_WHITE}{away_name}{Colors.RESET}")
            print_warning("A partida ainda não foi jogada.")
            return

        if m.get("winner_team_id"):
            print(f"\n  {Colors.B_GREEN}✓ Vencedor: {Colors.BOLD}{self._team_name(m['winner_team_id'])}{Colors.RESET}")

        goals = m.get("goals_by_player", [])
        if goals:
            print(f"\n  {Colors.CYAN}{'─'*40}{Colors.RESET}")
            print(f"  {Colors.BOLD}GOLS:{Colors.RESET}")
            for g in sorted(goals, key=lambda x: x.get("minute", 0)):
                player = self.player_service.get_player(g["player_id"])
                player_name = player["name"] if player else g["player_id"]
                team_name = self._team_name(g["team_id"])
                minute = g.get("minute", "?")
                print(f"  {Colors.B_YELLOW}⚽ {minute}'{Colors.RESET}  {Colors.B_WHITE}{player_name:<20}{Colors.RESET}  {Colors.B_BLACK}({team_name}){Colors.RESET}")
        else:
            print_info("Nenhum gol registrado (0 x 0).")

        if m.get("penalties_by_player"):
            print(f"\n  {Colors.RED}{'─'*40}{Colors.RESET}")
            print(f"  {Colors.BOLD}PÊNALTIS  ({m['penalties_home']} x {m['penalties_away']}){Colors.RESET}")
            for i, p_info in enumerate(m["penalties_by_player"], start=1):
                player = self.player_service.get_player(p_info["player_id"])
                player_name = player["name"] if player else p_info["player_id"]
                team_name = self._team_name(p_info["team_id"])
                icon = f"{Colors.B_GREEN}🟢 Gol{Colors.RESET}" if p_info["scored"] else f"{Colors.B_RED}🔴 Perdeu{Colors.RESET}"
                print(f"  {Colors.B_BLACK}{i}ª{Colors.RESET}  {Colors.B_WHITE}{player_name:<20}{Colors.RESET}  {Colors.DIM}({team_name}){Colors.RESET}  {icon}")

        print(f"\n{Colors.CYAN}{'═'*50}{Colors.RESET}")

    def edit_match_result(self, championship_id: str, championship: dict[str, Any]) -> None:
        played = [m for m in championship["matches"] if m["is_played"]]
        if not played:
            print("Nenhuma partida jogada para editar.")
            pause_screen()
            return

        played = sorted(played, key=lambda m: m["schedule_order"])
        print("\nPartidas jogadas:")
        for idx, m in enumerate(played, start=1):
            home = self._team_name(m["home_team_id"])
            away = self._team_name(m["away_team_id"])
            print(f"{idx:>2}) {home} {m['goals_home']} x {m['goals_away']} {away}")

        try:
            sel = ask_index("\nNúmero da partida para editar (0 cancelar): ", len(played), allow_cancel=True)
        except GoBackError:
            return
        if sel is None:
            return

        match = played[sel - 1]
        match_id = match["id"]
        home_team = self.team_service.get_team(match["home_team_id"])
        away_team = self.team_service.get_team(match["away_team_id"])

        clear_screen()
        print(f"\n--- Editando: {home_team['name']} {match['goals_home']} x {match['goals_away']} {away_team['name']} ---")
        print("Gols atuais:")
        for g in match.get("goals_by_player", []):
            player = self.player_service.get_player(g["player_id"])
            player_name = player["name"] if player else g["player_id"]
            team_name = self._team_name(g["team_id"])
            print(f"  ⚽ {g.get('minute', '?')}'\t{player_name}\t({team_name})")

        print("\n--- Re-registrando gols (começando do zero) ---")
        print("Comandos: gol (adicionar), desfazer (remover último), pronto (salvar)")

        new_goals: list[dict[str, Any]] = []
        home_score = 0
        away_score = 0

        while True:
            print(f"\nPlacar atual: {home_team['name']} {home_score} x {away_score} {away_team['name']} | Gols: {len(new_goals)}")
            try:
                cmd = handle_input("Comando (gol/desfazer/pronto): ").strip().lower()
            except GoBackError:
                try:
                    cancel = ask_choice("Cancelar edição sem salvar? (s/n): ", ["s", "n"])
                    if cancel == "s":
                        return
                except GoBackError:
                    pass
                continue

            if cmd == "gol":
                try:
                    team_opt = ask_choice(
                        f"Time (1={home_team['name']}, 2={away_team['name']}, 0=Cancelar): ",
                        ["1", "2", "0"],
                    )
                    if team_opt == "0":
                        continue
                    scoring_team = home_team if team_opt == "1" else away_team
                    players = scoring_team["player_ids"]
                    if not players:
                        print("Time sem jogadores.")
                        continue

                    print("Jogadores:")
                    for idx, pid in enumerate(players, start=1):
                        p = self.player_service.get_player(pid)
                        print(f"  {idx}) {p['name'] if p else pid}")

                    pidx = ask_index("Número do jogador (0 cancelar): ", len(players), allow_cancel=True)
                    if pidx is None:
                        continue
                    player_id = players[pidx - 1]

                    minute = ask_int("Minuto do gol: ", 1)

                    new_goals.append({
                        "player_id": player_id,
                        "team_id": scoring_team["id"],
                        "minute": minute,
                    })
                    if scoring_team["id"] == home_team["id"]:
                        home_score += 1
                    else:
                        away_score += 1
                    print("Gol adicionado.")
                except GoBackError:
                    continue

            elif cmd == "desfazer":
                if not new_goals:
                    print("Nenhum gol para desfazer.")
                else:
                    last = new_goals.pop()
                    if last["team_id"] == home_team["id"]:
                        home_score -= 1
                    else:
                        away_score -= 1
                    print("Último gol removido.")

            elif cmd == "pronto":
                try:
                    confirm = ask_choice(
                        f"Salvar novo resultado: {home_team['name']} {home_score} x {away_score} {away_team['name']}? (s/n): ",
                        ["s", "n"],
                    )
                    if confirm == "n":
                        continue
                except GoBackError:
                    continue

                penalties_home, penalties_away = None, None
                penalties_by_player = None
                if match["phase"] == "knockout" and home_score == away_score:
                    penalties_home, penalties_away, penalties_by_player = self._run_penalty_shootout(home_team, away_team)

                self.championship_service.edit_match_result(
                    championship_id, match_id, new_goals, penalties_home=penalties_home, penalties_away=penalties_away, penalties_by_player=penalties_by_player
                )
                print("Resultado atualizado com sucesso!")
                pause_screen()
                return
            else:
                print("Comando inválido. Use: gol, desfazer, pronto")

    def stats_menu(self) -> None:
        while True:
            clear_screen()
            print_header("Estatísticas e Histórico", color=Colors.MAGENTA)
            print(f"{Colors.CYAN}1){Colors.RESET} Estatísticas Gerais")
            print(f"{Colors.CYAN}2){Colors.RESET} Desempenho Completo dos Jogadores")
            print(f"{Colors.CYAN}3){Colors.RESET} Histórico de Todas as Partidas")
            print(f"{Colors.RED}0){Colors.RESET} Voltar")
            try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "0"])
            except GoBackError:
                return

            if choice == "1":
                self._print_general_stats()
                pause_screen()
            elif choice == "2":
                self._print_all_players_stats()
                pause_screen()
            elif choice == "3":
                self._print_all_matches_history()
                pause_screen()
            else:
                return

    def _print_general_stats(self) -> None:
        championships = self.championship_service.list_championships()
        stats = self.stats_service.aggregate(championships)

        print_header("Estatísticas Gerais", color=Colors.MAGENTA)
        print(f"  {Colors.B_BLACK}Total de campeonatos:{Colors.RESET} {Colors.BOLD}{stats['championship_count']}{Colors.RESET}")

        if stats["best_player"]:
            best = stats["best_player"]
            print(f"  {Colors.B_YELLOW}⭐ Artilheiro geral:{Colors.RESET} {Colors.BOLD}{best['player_name']}{Colors.RESET} ({Colors.CYAN}{best['goals']} gols{Colors.RESET})")
        else:
            print_info("Artilheiro: sem dados ainda.")

        print(f"\n  {Colors.BOLD}{Colors.CYAN}Top Jogadores (Artilheiros):{Colors.RESET}")
        if not stats["top_players"]:
            print_warning("Sem gols registrados.")
        else:
            rows = [[str(i), p['player_name'], str(p['goals'])] for i, p in enumerate(stats['top_players'][:10], 1)]
            format_table(["#", "Jogador", "Gols"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.B_YELLOW])

        print(f"\n  {Colors.BOLD}{Colors.CYAN}Times com mais títulos:{Colors.RESET}")
        if not stats["top_teams_by_titles"]:
            print_warning("Sem campeões definidos ainda.")
        else:
            rows = [[str(i), t['team_name'], str(t['titles'])] for i, t in enumerate(stats['top_teams_by_titles'], 1)]
            format_table(["#", "Time", "Títulos"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.B_YELLOW])

        print(f"\n  {Colors.BOLD}{Colors.CYAN}Gols por fase:{Colors.RESET}")
        if not stats["goals_by_phase"]:
            print_warning("Sem partidas jogadas ainda.")
        else:
            rows = [[phase, str(goals)] for phase, goals in stats["goals_by_phase"].items()]
            format_table(["Fase", "Gols"], rows, [Colors.MAGENTA, Colors.B_YELLOW])

        print(f"\n  {Colors.BOLD}{Colors.CYAN}Tendência Histórica (gols por campeonato):{Colors.RESET}")
        if not stats["historical_trend"]:
            print_warning("Sem histórico.")
        else:
            rows = []
            for row in stats["historical_trend"]:
                delta = row["delta_vs_previous"]
                delta_label = "N/A" if delta is None else (f"+{delta}" if delta >= 0 else str(delta))
                rows.append([row['name'], row['created_at'][:10], str(row['total_goals']), delta_label])
            format_table(["Campeonato", "Data", "Gols", "Δ"], rows, [Colors.B_WHITE, Colors.B_BLACK, Colors.CYAN, Colors.B_YELLOW])

    def _print_all_players_stats(self) -> None:
        championships = self.championship_service.list_championships()
        details = self.stats_service.get_all_players_details(championships)
        
        print_header("Desempenho Completo dos Jogadores", color=Colors.MAGENTA)
        if not details:
            print_warning("Sem dados de jogadores.")
            return

        scorers = [d for d in details if d['total_goals'] > 0]
        if not scorers:
            print_info("Nenhum jogador marcou gols ainda.")
            return

        for d in scorers:
            stars_str = f"{'★' * d['stars']}{'☆' * (5 - d['stars'])}"
            print(f"\n  {Colors.BOLD}{Colors.B_WHITE}{d['name']}{Colors.RESET}  {Colors.YELLOW}{stars_str}{Colors.RESET}")
            print(f"  {Colors.B_BLACK}Total de Gols:{Colors.RESET} {Colors.B_YELLOW}{d['total_goals']}{Colors.RESET}")
            print(f"  {Colors.B_BLACK}Times:{Colors.RESET} {Colors.CYAN}{', '.join(d['teams_scored_for']) if d['teams_scored_for'] else '-'}{Colors.RESET}")
            if d['goals_by_championship']:
                rows = [[c_name, str(count)] for c_name, count in d['goals_by_championship'].items()]
                format_table(["Campeonato", "Gols"], rows, [Colors.B_WHITE, Colors.B_YELLOW])

    def _print_all_matches_history(self) -> None:
        championships = self.championship_service.list_championships()
        matches = self.stats_service.get_all_matches_details(championships)
        
        print_header("Histórico de Todas as Partidas", color=Colors.MAGENTA)
        if not matches:
            print_warning("Ainda não há histórico de partidas jogadas.")
            return

        rows = []
        for idx, m in enumerate(matches, start=1):
            home_name = self._team_name(m["home_team_id"])
            away_name = self._team_name(m["away_team_id"])
            p_date = (m.get("played_at") or "-")[:10]
            c_name = m["championship_name"]
            grp = f"G.{m['group_name']}" if m.get("group_name") else m.get("round_name", "-")
            phase = m.get("phase", "?").upper()
            score_str = f"{m.get('goals_home', 0)} x {m.get('goals_away', 0)}"
            if m.get("penalties_home") is not None:
                score_str += f" ({m['penalties_home']}x{m['penalties_away']})"
            rows.append([str(idx), c_name, phase, grp, home_name, score_str, away_name, p_date])
        format_table(
            ["#", "Campeonato", "Fase", "Grupo", "Casa", "Placar", "Fora", "Data"],
            rows,
            [Colors.B_BLACK, Colors.CYAN, Colors.MAGENTA, Colors.B_BLACK, Colors.B_WHITE, Colors.B_YELLOW, Colors.B_WHITE, Colors.B_BLACK]
        )


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
        pause_event = threading.Event()

        def timer_thread() -> None:
            while remaining["seconds"] > 0 and not stop_event.is_set():
                is_paused = pause_event.is_set()
                mins = remaining["seconds"] // 60
                secs = remaining["seconds"] % 60
                status = " (PAUSADA ⏸️)" if is_paused else ""
                sys.stdout.write(f"\0337\033[2;1H\033[K⏱️  Tempo restante: {mins:02d}:{secs:02d}{status}\0338")
                sys.stdout.flush()
                time.sleep(1)
                if not is_paused:
                    remaining["seconds"] -= 1

            if not stop_event.is_set():
                time_up_event.set()
                sys.stdout.write(f"\0337\033[2;1H\033[K⏱️  TEMPO ENCERRADO!\0338")
                sys.stdout.flush()

        clear_screen()
        print(
            f"Partida iniciada: {home_team['name']} x {away_team['name']} | "
            f"Duração: {match['duration_minutes']} minuto(s).\n"
        )
        print("\nComandos: gol, placar, pausa, +1, -1, fim\n")

        t = threading.Thread(target=timer_thread, daemon=True)
        t.start()

        while not time_up_event.is_set():
            try:
                cmd = handle_input("\nComando: ").strip().lower()
            except GoBackError:
                print("Operação reversa apenas disponivel com comando 'desfazer'.")
                continue

            if cmd == "gol":
                try:
                    team_opt = ask_choice(
                        f"Time do gol (1={home_team['name']}, 2={away_team['name']}, 0=Cancelar): ",
                        ["1", "2", "0", "c"],
                    )
                    if team_opt in ("0", "c"):
                        print("Ação cancelada.")
                        continue
                    scoring_team = home_team if team_opt == "1" else away_team
                    players = scoring_team["player_ids"]
                    if not players:
                        print("Este time não possui jogadores cadastrados para marcar gol.")
                        continue
    
                    print("Jogadores disponíveis:")
                    for idx, pid in enumerate(players, start=1):
                        p = self.player_service.get_player(pid)
                        print(f"{idx}) {p['name'] if p else pid}")
    
                    sel = ask_index("Número do jogador (0 para cancelar): ", len(players), allow_cancel=True)
                    if sel is None:
                        continue
                    player_id = players[sel - 1]
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
                except GoBackError:
                    print("Operação de gol vazia.")
                    continue

            elif cmd == "placar":
                print(f"Placar atual: {home_team['name']} {home_score} x {away_score} {away_team['name']}")
            elif cmd in ("desfazer", "cancelar_gol", "cancelar"):
                if not goals_by_player:
                    print("Nenhum gol registrado para desfazer.")
                else:
                    last_goal = goals_by_player.pop()
                    if last_goal["team_id"] == home_team["id"]:
                        home_score -= 1
                    else:
                        away_score -= 1
                    print("Último gol anulado com sucesso.")
            elif cmd in ("pausa", "pausar"):
                if pause_event.is_set():
                    pause_event.clear()
                    print("▶️ Partida retomada.")
                else:
                    pause_event.set()
                    print("⏸️ Partida pausada.")
            elif cmd == "fim":
                try:
                    confirm = ask_choice("Encerrar partida agora? (s/n): ", ["s", "n"])
                    if confirm == "s":
                        stop_event.set()
                        break
                except GoBackError:
                    continue
            elif cmd.startswith("+") and cmd[1:].isdigit():
                remaining["seconds"] += int(cmd[1:]) * 60
                print(f"Adicionou {cmd[1:]} minuto(s).")
            elif cmd.startswith("-") and cmd[1:].isdigit():
                remaining["seconds"] = max(0, remaining["seconds"] - int(cmd[1:]) * 60)
                print(f"Removeu {cmd[1:]} minuto(s).")
            else:
                print("Comando inválido. Use: gol, placar, pausa, +N, -N, desfazer, fim")

        stop_event.set()
        t.join(timeout=1)
        print(f"Placar final: {home_team['name']} {home_score} x {away_score} {away_team['name']}")
        return goals_by_player

    def create_team_manually(self) -> None:
        clear_screen()
        players = self.player_service.list_players()
        if not players:
            print_warning("Cadastre jogadores antes de criar times.")
            return

        state = 0
        t_name = ""
        while True:
            try:
                if state == 0:
                    print_header("Criar Time", color=Colors.CYAN)
                    rows = [[str(i), p['name'], '★'*p['stars']+'☆'*(5-p['stars'])] for i, p in enumerate(players, 1)]
                    format_table(["#", "Jogador", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])
                    t_name = ask_non_empty("Nome do time: ")
                    state += 1
                elif state == 1:
                    indices = ask_multi_index("Números dos jogadores (CSV): ", len(players))
                    player_ids = [players[i - 1]['id'] for i in indices]
                    team = self.team_service.create_team(t_name, player_ids)
                    print_success(f"Time '{team['name']}' criado.")
                    break
            except GoBackError:
                if state == 0: break
                state -= 1

    def edit_team(self) -> None:
        clear_screen()
        teams = self.team_service.list_teams()
        if not teams:
            print_warning("Nenhum time encontrado.")
            return

        state = 0
        team: dict[str, Any] | None = None
        team_id = ""
        t_name = ""
        while True:
            try:
                if state == 0:
                    print_header("Editar Time", color=Colors.CYAN)
                    rows = [[str(i), t['name']] for i, t in enumerate(teams, 1)]
                    format_table(["#", "Time"], rows, [Colors.B_BLACK, Colors.B_WHITE])
                    sel = ask_index("Número do time (0 para cancelar): ", len(teams), allow_cancel=True)
                    if sel is None:
                        break
                    team = teams[sel - 1]
                    team_id = team['id']
                    state += 1
                elif state == 1:
                    self._print_team(team)
                    t_name = handle_input(f"Novo nome [{team['name']}]: ").strip() or team['name']
                    state += 1
                elif state == 2:
                    players = self.player_service.list_players()
                    print_header("Selecionar Jogadores", color=Colors.CYAN)
                    rows = [[str(i), p['name'], '★'*p['stars']+'☆'*(5-p['stars'])] for i, p in enumerate(players, 1)]
                    format_table(["#", "Jogador", "Estrelas"], rows, [Colors.B_BLACK, Colors.B_WHITE, Colors.YELLOW])
                    indices = ask_multi_index("Novos números dos jogadores (CSV): ", len(players))
                    player_ids = [players[i - 1]['id'] for i in indices]
                    self.team_service.update_team(team_id, t_name, player_ids)
                    print_success("Time atualizado.")
                    break
            except GoBackError:
                if state == 0: break
                state -= 1

    def _print_teams(self) -> None:
        active = self.team_service.list_teams()
        archived = self.team_service.list_archived_teams()

        if not active and not archived:
            print_warning("Nenhum time cadastrado.")
            return

        if active:
            print_header("Times Ativos", color=Colors.CYAN)
            rows = []
            for t in active:
                member_names = []
                for pid in t["player_ids"]:
                    p = self.player_service.get_player(pid)
                    member_names.append(p["name"] if p else pid)
                ch_label = ""
                if t.get("championship_id"):
                    ch = self.championship_service.get_championship(t["championship_id"])
                    ch_label = ch["name"] if ch else t["championship_id"]
                color_str = self._team_color_ansi(t["name"]) + t["name"] + Colors.RESET
                rows.append([color_str, ch_label, ", ".join(member_names) or "(nenhum)"])
            format_table(["Time", "Campeonato", "Jogadores"], rows, [None, Colors.CYAN, Colors.B_BLACK])

        if archived:
            print_header("Times Históricos (Arquivados)", color=Colors.MAGENTA)
            rows = []
            for t in archived:
                member_names = []
                for pid in t["player_ids"]:
                    p = self.player_service.get_player(pid)
                    member_names.append(p["name"] if p else pid)
                ch_label = ""
                if t.get("championship_id"):
                    ch = self.championship_service.get_championship(t["championship_id"])
                    ch_label = ch["name"] if ch else t["championship_id"]
                rows.append([t["name"], ch_label, ", ".join(member_names) or "(nenhum)"])
            format_table(["Time", "Campeonato", "Jogadores"], rows, [Colors.DIM, Colors.B_BLACK, Colors.B_BLACK])

    def _print_team(self, team: dict[str, Any]) -> None:
        names = []
        for pid in team["player_ids"]:
            player = self.player_service.get_player(pid)
            names.append(player["name"] if player else pid)
        color = self._team_color_ansi(team['name'])
        print(f"Time: {color}{team['name']}{Colors.RESET}  Jogadores: {', '.join(names) or '(nenhum)'}")

    def _team_color_ansi(self, team_name: str) -> str:
        """Return an ANSI color code matching the team's color word in its name."""
        from app.services.team_generator import COLORS
        # Map color word -> ANSI code
        color_map: dict[str, str] = {
            "Azul":     Colors.BLUE,
            "Vermelho": Colors.RED,
            "Verde":    Colors.GREEN,
            "Amarelo":  Colors.YELLOW,
            "Branco":   Colors.B_WHITE,
            "Preto":    Colors.B_BLACK,
            "Laranja":  Colors.B_RED,
            "Roxo":     Colors.MAGENTA,
            "Cinza":    Colors.WHITE,
            "Rosa":     Colors.B_MAGENTA,
            "Marrom":   Colors.RED,
            "Ciano":    Colors.CYAN,
        }
        for word, code in color_map.items():
            if word.lower() in team_name.lower():
                return f"{Colors.BOLD}{code}"
        return Colors.B_WHITE

    def _team_name(self, team_id: str | None) -> str:
        if not team_id:
            return "BYE"
        # search active + archived
        all_teams = self.team_service._load()
        t = next((t for t in all_teams if t["id"] == team_id), None)
        if not t:
            return team_id
        return self._team_color_ansi(t["name"]) + t["name"] + Colors.RESET
