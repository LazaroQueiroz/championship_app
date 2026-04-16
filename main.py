from pathlib import Path

from app.cli import ChampionshipCLI


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    ChampionshipCLI(base_dir).run()
