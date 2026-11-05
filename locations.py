"""Regras das prateleiras, independentes da interface e do Google Sheets."""

HEADERS = ["Referencia", "Prateleira", "Divisao", "Observacao"]
SHELVES = [f"P{i}" for i in range(1, 15)]


def divisions(shelf):
    if shelf not in SHELVES:
        raise ValueError("Prateleira inválida. Escolha P1 a P14.")
    count = 4 if shelf in ("P1", "P2") else 5
    return [f"{row}{i}" for row in "AB" for i in range(1, count + 1)]


def validate(reference, shelf, division, observation=""):
    reference = str(reference).strip()
    shelf = str(shelf).strip().upper()
    division = str(division).strip().upper()
    if not reference:
        raise ValueError("Informe a referência do tecido.")
    if division not in divisions(shelf):
        raise ValueError("Divisão inválida para essa prateleira.")
    return [reference, shelf, division, str(observation).strip()]


def table_entries(values):
    if not values:
        return []
    if values[0] not in (HEADERS, HEADERS[:3]):
        raise ValueError("A primeira linha deve conter: Referencia | Prateleira | Divisao | Observacao. Não altere as três primeiras colunas.")
    entries = []
    for number, cells in enumerate(values[1:], start=2):
        if not any(cells):
            continue
        if len(cells) > 4 or len(cells) < 3:
            raise ValueError(f"Confira os campos da linha {number} da planilha.")
        entries.append((number, dict(zip(HEADERS, validate(*cells)))))
    return entries


def location_key(record):
    return (record["Referencia"].casefold(), record["Prateleira"], record["Divisao"])


def plan_save(values, row, current=None):
    """Planeja a gravação sem modificar a planilha; preserva outras divisões."""
    row = validate(*row)
    entries = table_entries(values)
    target = dict(zip(HEADERS, row))
    source = None
    if current is not None:
        sources = [number for number, record in entries if location_key(record) == location_key(current)]
        if len(sources) != 1:
            raise ValueError("A localização original mudou ou está repetida. Reabra o cadastro antes de salvar.")
        source = sources[0]
    occupants = [(number, record) for number, record in entries
        if (record["Prateleira"], record["Divisao"]) == (row[1], row[2])]
    if any(location_key(record) == location_key(target) and number != source for number, record in occupants):
        raise ValueError("Essa referência já está cadastrada nessa prateleira e divisão.")
    displaced = [(number, record) for number, record in occupants if number != source]
    destination = occupants[0][0] if occupants else source
    updates = []
    if destination is not None:
        updates.append({"range": f"A{destination}:D{destination}", "values": [row]})
        clear_rows = {number for number, _ in occupants if number != destination}
        if source is not None and source != destination:
            clear_rows.add(source)
        for number in sorted(clear_rows):
            updates.append({"range": f"A{number}:D{number}", "values": [["", "", "", ""]]})
    return {"row": row, "updates": updates, "append": destination is None,
        "replaced": [record["Referencia"] for _, record in displaced]}


def plan_release(values, current):
    """Libera somente a divisão escolhida, incluindo eventuais registros antigos."""
    occupants = [(number, record) for number, record in table_entries(values)
        if (record["Prateleira"], record["Divisao"]) == (current["Prateleira"], current["Divisao"])]
    if not any(location_key(record) == location_key(current) for _, record in occupants):
        raise ValueError("Este cadastro mudou ou já foi removido. Confira a divisão novamente.")
    return {
        "shelf": current["Prateleira"], "division": current["Divisao"],
        "references": [record["Referencia"] for _, record in occupants],
        "updates": [{"range": f"A{number}:D{number}", "values": [["", "", "", ""]]}
            for number, _ in occupants],
    }


def plan_observation(values, current, observation):
    matches = [(number, record) for number, record in table_entries(values)
        if location_key(record) == location_key(current)]
    if len(matches) != 1 or matches[0][1] != current:
        raise ValueError("Este cadastro mudou. Volte e abra a localização novamente antes de editar.")
    number, _ = matches[0]
    return [{"range": "A1:D1", "values": [HEADERS]},
        {"range": f"D{number}", "values": [[str(observation).strip()]]}]
