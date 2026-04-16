from __future__ import annotations

import uuid
from datetime import datetime


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ask_int(prompt: str, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Valor inválido. Digite um número inteiro.")
            continue

        if min_value is not None and value < min_value:
            print(f"Valor deve ser >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Valor deve ser <= {max_value}.")
            continue
        return value


def ask_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Campo obrigatório.")


def ask_choice(prompt: str, choices: list[str]) -> str:
    valid = {c.lower(): c for c in choices}
    while True:
        raw = input(prompt).strip().lower()
        if raw in valid:
            return valid[raw]
        print(f"Escolha inválida. Opções: {', '.join(choices)}")
