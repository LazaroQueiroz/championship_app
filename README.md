# Championship App

Gerenciador de campeonatos com fase de grupos, mata-mata e estatísticas detalhadas.  
Interface de linha de comando com cores ANSI, tabelas alinhadas e navegação reversível.

## Rodando no computador

```bash
python main.py
```

**Requisitos:** Python 3.10+. Sem dependências externas.

---

## Rodando no celular

### Android — Termux (recomendado)

1. Instale o **Termux** pelo [F-Droid](https://f-droid.org/packages/com.termux/) *(não use a versão da Play Store — está desatualizada)*
2. Abra o Termux e execute:

```bash
pkg update && pkg install python git
git clone https://github.com/SEU_USUARIO/championship_app.git
cd championship_app
python main.py
```

> **Dica:** Use uma fonte monoespaçada e ative cores Unicode nas configurações do Termux para a melhor experiência.

### iPhone — a-Shell

1. Instale o **[a-Shell](https://apps.apple.com/app/a-shell/id1473805438)** pela App Store
2. O a-Shell já vem com Python 3. Execute:

```bash
git clone https://github.com/SEU_USUARIO/championship_app.git
cd championship_app
python main.py
```

---

## Acesso remoto por SSH (alternativa mais simples)

Se o app já roda no seu computador, você pode acessá-lo do celular via SSH — sem precisar instalar nada localmente.

1. No celular, instale **Termius** ou **JuiceSSH**
2. Conecte no IP da sua máquina (ex: `192.168.1.x`) na porta 22
3. Navegue até a pasta e execute `python main.py`

Os dados ficam centralizados na máquina — sem sincronização necessária.

---

## Navegação

| Comando | Ação |
|---------|------|
| Número + Enter | Selecionar opção |
| `<` + Enter | Voltar ao passo anterior |
| `0` + Enter | Cancelar/voltar ao menu |

## Durante uma partida ao vivo

| Comando | Ação |
|---------|------|
| `gol` | Registrar gol |
| `desfazer` | Anular último gol |
| `placar` | Ver placar atual |
| `pausa` | Pausar/retomar timer |
| `+N` | Adicionar N minutos (ex: `+2`) |
| `-N` | Remover N minutos (ex: `-1`) |
| `fim` | Encerrar partida |
