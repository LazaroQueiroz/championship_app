from __future__ import annotations

import uuid
from datetime import datetime


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

class GoBackError(Exception):
    """Raised when the user requests to return to the previous state with '<'."""
    pass

def handle_input(prompt: str) -> str:
    """Wrapper around standard input that intercepts the global back command."""
    raw = input(prompt)
    if raw.strip() == "<":
        raise GoBackError()
    return raw

def ask_int(prompt: str, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = handle_input(prompt).strip()
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
        value = handle_input(prompt).strip()
        if value:
            return value
        print("Campo obrigatório.")


def ask_choice(prompt: str, choices: list[str]) -> str:
    valid = {c.lower(): c for c in choices}
    while True:
        raw = handle_input(prompt).strip().lower()
        if raw in valid:
            return valid[raw]
        print(f"Escolha inválida. Opções: {', '.join(choices)}")


def clear_screen() -> None:
    import os
    os.system("cls" if os.name == "nt" else "clear")


def pause_screen() -> None:
    input("\nPressione Enter para continuar...")


def ask_index(prompt: str, max_index: int, allow_cancel: bool = False) -> int | None:
    """Ask the user for an index between 1 and max_index. If allow_cancel is True, 0 or 'c' returns None."""
    while True:
        raw = handle_input(prompt).strip().lower()
        if allow_cancel and raw in ("0", "c", "cancelar"):
            return None
        try:
            value = int(raw)
            if 1 <= value <= max_index:
                return value
            print(f"Índice fora do limite. Escolha um número entre 1 e {max_index}.")
        except ValueError:
            print("Valor inválido. Digite um número.")


def ask_multi_index(prompt: str, max_index: int, allow_empty: bool = False) -> list[int]:
    """Ask the user to input multiple indices separated by commas."""
    while True:
        raw = handle_input(prompt).strip()
        if not raw:
            if allow_empty:
                return []
            print("Campo obrigatório.")
            continue
        parts = [p.strip() for p in raw.split(",")]
        try:
            indices = []
            for p in parts:
                if p:
                    val = int(p)
                    if not (1 <= val <= max_index):
                        raise ValueError(f"{val} fora do limite.")
                    indices.append(val)
            if not indices:
                raise ValueError("Nenhum índice informado.")
            return indices
        except ValueError as e:
            print(f"Entrada inválida ({e}). Use números separados por vírgula. Ex: 1, 3")
