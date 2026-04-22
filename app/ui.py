from typing import Any

# Color Palette ANSI Escape Codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"

    # Standard
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright
    B_BLACK = "\033[90m"
    B_RED = "\033[91m"
    B_GREEN = "\033[92m"
    B_YELLOW = "\033[93m"
    B_BLUE = "\033[94m"
    B_MAGENTA = "\033[95m"
    B_CYAN = "\033[96m"
    B_WHITE = "\033[97m"


def _visual_len(s: str) -> int:
    """Return the visible terminal width of a string.
    Emoji and other wide characters occupy 2 columns each."""
    width = 0
    for ch in s:
        cp = ord(ch)
        # Wide emoji ranges (approximate but covers common cases)
        if (
            0x1F300 <= cp <= 0x1FAFF  # Misc symbols / emoji
            or 0x2600 <= cp <= 0x27BF  # Misc symbols
            or 0x2300 <= cp <= 0x23FF  # Tech symbols (⏳ etc)
            or 0x231A <= cp <= 0x231B
            or 0x23E9 <= cp <= 0x23F3
            or 0x25AA <= cp <= 0x25FE
            or 0x2614 <= cp <= 0x2615
            or 0x2648 <= cp <= 0x2653
            or 0x267F == cp
            or 0x2693 == cp
            or 0x26A1 == cp
            or 0x26AA <= cp <= 0x26AB
            or 0x26BD <= cp <= 0x26BE
            or 0x26C4 <= cp <= 0x26C5
            or 0x26CE == cp
            or 0x26D4 == cp
            or 0x26EA == cp
            or 0x26F2 <= cp <= 0x26F3
            or 0x26F5 == cp
            or 0x26FA == cp
            or 0x26FD == cp
            or 0x2702 == cp
            or 0x2705 == cp  # ✅
            or 0x2708 <= cp <= 0x270D
            or 0x270F == cp
            or 0x2712 == cp
            or 0x2714 == cp
            or 0x2716 == cp
            or 0x271D == cp
            or 0x2721 == cp
            or 0x2728 == cp
            or 0x2733 <= cp <= 0x2734
            or 0x2744 == cp
            or 0x2747 == cp
            or 0x274C == cp
            or 0x274E == cp
            or 0x2753 <= cp <= 0x2755
            or 0x2757 == cp
            or 0x2763 <= cp <= 0x2764
            or 0x2795 <= cp <= 0x2797
            or 0x27A1 == cp
            or 0x27B0 == cp
            or 0x27BF == cp
            or 0xFE0F == cp  # variation selector (zero-width, but skip)
        ):
            # Variation selector is truly zero width
            if cp == 0xFE0F:
                width += 0
            else:
                width += 2
        else:
            width += 1
    return width


def _pad_cell(text: str, total_width: int) -> str:
    """Left-pad a cell to total_width using visual width, not len()."""
    vlen = _visual_len(text)
    padding = max(0, total_width - vlen)
    return text + " " * padding


def print_header(title: str, character: str = "═", color: str = Colors.CYAN) -> None:
    """Prints a styled header panel."""
    width = 60
    padded = f" {title.upper()} "
    left_padding = (width - len(padded)) // 2
    right_padding = width - len(padded) - left_padding

    print(f"\n{color}{character * width}")
    print(f"{character * left_padding}{Colors.BOLD}{padded}{Colors.RESET}{color}{character * right_padding}")
    print(f"{character * width}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Prints a green success log."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Prints a red error log."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Prints a yellow warning log."""
    print(f"{Colors.YELLOW}⚠  {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Prints a blue info log."""
    print(f"{Colors.BLUE}ℹ  {message}{Colors.RESET}")


def format_table(headers: list[str], rows: list[list[Any]], col_colors: list[str] | None = None) -> None:
    """Prints a formatted grid table with correct emoji-aware column alignment."""
    if not headers and not rows:
        return

    str_rows = [[str(cell) for cell in row] for row in rows]

    # Calculate column widths using visual length
    col_widths = [_visual_len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], _visual_len(cell))

    # Add 2 chars of padding (1 each side)
    col_widths = [w + 2 for w in col_widths]

    sep_top = f"{Colors.B_BLACK}┌" + "┬".join("─" * w for w in col_widths) + f"┐{Colors.RESET}"
    sep_mid = f"{Colors.B_BLACK}├" + "┼".join("─" * w for w in col_widths) + f"┤{Colors.RESET}"
    sep_bot = f"{Colors.B_BLACK}└" + "┴".join("─" * w for w in col_widths) + f"┘{Colors.RESET}"

    # Header row
    print(sep_top)
    hrow = f"{Colors.B_BLACK}│{Colors.RESET}"
    for i, h in enumerate(headers):
        inner = col_widths[i] - 2  # space for 1-char pad each side
        hrow += f"{Colors.BOLD} {_pad_cell(h, inner)} {Colors.RESET}{Colors.B_BLACK}│{Colors.RESET}"
    print(hrow)
    print(sep_mid)

    # Data rows
    for row in str_rows:
        rstr = f"{Colors.B_BLACK}│{Colors.RESET}"
        for i, cell in enumerate(row):
            inner = col_widths[i] - 2
            color = col_colors[i] if col_colors and i < len(col_colors) and col_colors[i] else ""
            rstr += f"{color} {_pad_cell(cell, inner)} {Colors.RESET}{Colors.B_BLACK}│{Colors.RESET}"
        print(rstr)

    print(sep_bot)
