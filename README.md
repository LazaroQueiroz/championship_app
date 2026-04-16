# Championship Management App (CLI)

Aplicação de terminal em Python para gerenciar jogadores, times e campeonatos com fase de grupos + mata-mata.

## Funcionalidades

- CRUD de **jogadores** (nome e estrelas de 0 a 5)
- CRUD de **times** (nome e lista de jogadores)
- Persistência em **JSON**
- Geração de times balanceados por estrelas (snake draft)
- Criação de campeonato com:
  - Fase de grupos (todos contra todos)
  - Agenda de partidas com tentativa de evitar jogos consecutivos do mesmo time
  - Registro de gols por jogador
  - Timer em tempo real por partida
  - Mata-mata gerado a partir da classificação dos grupos
- Estatísticas:
  - Artilheiro geral
  - Comparativo entre campeonatos
  - Tendência histórica (gols por campeonato)
  - Times com mais títulos

## Estrutura

```text
championship_app/
├── app/
│   ├── cli.py
│   ├── storage.py
│   ├── utils.py
│   └── services/
│       ├── player_service.py
│       ├── team_service.py
│       ├── team_generator.py
│       ├── championship_service.py
│       └── stats_service.py
├── data/
│   ├── players.json
│   ├── teams.json
│   └── championships.json
└── main.py
```

## Como executar

Requisitos: Python 3.10+

```bash
cd /home/ubuntu/championship_app
python3 main.py
```

## Fluxo sugerido

1. Cadastre jogadores
2. Crie times manualmente ou use geração balanceada
3. Crie um campeonato selecionando times e quantidade de grupos
4. Registre partidas com timer em tempo real (comandos: `gol`, `placar`, `fim`)
5. Quando grupos terminarem, gere mata-mata
6. Continue registrando partidas até definir campeão
7. Veja estatísticas e histórico no menu principal

## Regras implementadas

- Classificação dos grupos: **pontos** e depois **saldo de gols** (SG)
- Em mata-mata: empate exige escolha manual do vencedor no desempate
- Persistência automática a cada operação

## Observações

- Em terminal, o timer e prompts podem se sobrepor visualmente em alguns momentos; isso não afeta o registro dos dados.
- Os arquivos JSON em `data/` podem ser apagados para reiniciar o sistema.
