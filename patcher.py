import re

with open("app/cli.py", "r") as f:
    code = f.read()

# 1. Championships menu missing 4
code = code.replace(
    'print("3) Gerenciar campeonato")\n            print("0) Voltar")',
    'print("3) Gerenciar campeonato")\n            print("4) Excluir campeonato")\n            print("0) Voltar")'
)

code = code.replace(
    'choice = ask_choice("Escolha: ", ["1", "2", "3", "0"])',
    '''try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "0"])
            except GoBackError:
                return'''
)

code = code.replace(
    'self.manage_championship()\n                else:',
    '''self.manage_championship()
                elif choice == "4":
                    self.list_championships()
                    champs = self.championship_service.list_championships()
                    if champs:
                        try:
                            sel = ask_index("\\nNúmero do campeonato para excluir (0 cancelar): ", len(champs), allow_cancel=True)
                        except GoBackError:
                            continue
                        if sel is not None:
                            self.championship_service.delete_championship(champs[sel - 1]['id'])
                            print("Campeonato apagado definitivamente.")
                else:'''
)

# 2. manage_championship
code = code.replace(
    'championship_id = ask_non_empty("ID do campeonato: ")',
    '''champs = self.championship_service.list_championships()
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
            return'''
)

code = code.replace(
    'choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "0"])',
    '''try:
                choice = ask_choice("Escolha: ", ["1", "2", "3", "4", "5", "6", "7", "0"])
            except GoBackError:
                return'''
)

# 3. create_championship state loop
create_match = r"""    def create_championship(self) -> None:
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
        print(f"Campeonato criado com ID: {ch['id']}")"""

new_create_match = """    def create_championship(self) -> None:
        teams = self.team_service.list_teams()
        
        state = 0
        name = ""
        opt = ""
        team_ids = []
        group_count = 1
        duration = 1
        
        while True:
            try:
                if state == 0:
                    name = ask_non_empty("Nome do campeonato: ")
                    state += 1
                elif state == 1:
                    print("\\n1) Usar times existentes\\n2) Sorteio Automático Equilibrado de Jogadores (Draft)\\n0) Voltar")
                    opt = ask_choice("Escolha (1/2/0): ", ["1", "2", "0"])
                    if opt == "0":
                        raise GoBackError()
                    state += 1
                elif state == 2:
                    if opt == "1":
                        if len(teams) < 2:
                            print("Cadastre ao menos 2 times de antemão.")
                            raise GoBackError()
                        print("Times disponíveis:")
                        for idx, t in enumerate(teams, start=1):
                            print(f"{idx}) {t['name']}")
                        indices = ask_multi_index("Números dos times participantes (separados por vírgula): ", len(teams))
                        team_ids = [teams[i - 1]['id'] for i in indices]
                    else:
                        all_players = self.player_service.list_players()
                        qty_teams = ask_int("\\nQuantos times deseja sortear? (Mínimo 2): ", 2, len(all_players))
                        
                        absent_indices = ask_multi_index("Jogadores ausentes (números CSV, ou Enter pra NENHUM): ", len(all_players), allow_empty=True)
                        absent_ids = [all_players[i-1]['id'] for i in absent_indices]
                        active_players = [p for p in all_players if p['id'] not in absent_ids]
                        
                        generated = generate_balanced_teams(active_players, qty_teams)
                        team_ids = []
                        for t in generated:
                            t_name = f"Time Temp {t['slot']} (Draft)"
                            p_ids = [p['id'] for p in t['players']]
                            t_model = self.team_service.create_team(t_name, p_ids)
                            team_ids.append(t_model['id'])
                    state += 1
                elif state == 3:
                    group_count = ask_int("\\nNúmero de grupos: ", 1, len(team_ids))
                    state += 1
                elif state == 4:
                    duration = ask_int("Duração de cada partida (em minutos): ", 1)
                    ch = self.championship_service.create_championship(name, team_ids, group_count, duration)
                    print(f"\\nCampeonato criado com sucesso!")
                    break
            except GoBackError:
                if state == 0: break
                state -= 1"""

code = code.replace(create_match, new_create_match)

with open("app/cli.py", "w") as f:
    f.write(code)

