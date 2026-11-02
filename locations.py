"""Regras das prateleiras, independentes da interface e do Google Sheets."""

HEADERS = ["Referencia", "Prateleira", "Divisao"]
SHELVES = [f"P{i}" for i in range(1, 15)]


def divisions(shelf):
    if shelf not in SHELVES:
        raise ValueError("Prateleira inválida. Escolha P1 a P14.")
    count = 4 if shelf in ("P1", "P2") else 5
    return [f"{row}{i}" for row in "AB" for i in range(1, count + 1)]


def validate(reference, shelf, division):
    reference = str(reference).strip()
    shelf = str(shelf).strip().upper()
    division = str(division).strip().upper()
    if not reference:
        raise ValueError("Informe a referência do tecido.")
    if division not in divisions(shelf):
        raise ValueError("Divisão inválida para essa prateleira.")
    return [reference, shelf, division]


def location_key(record):
    return (record["Referencia"].casefold(), record["Prateleira"], record["Divisao"])
