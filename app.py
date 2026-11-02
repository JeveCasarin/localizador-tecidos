import csv
import html
import io

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from locations import HEADERS, SHELVES, divisions, validate

st.set_page_config(page_title="Localizador de Tecidos", page_icon="🧵", layout="wide")


@st.cache_resource
def connect():
    credentials = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    config = st.secrets["google_sheet"]
    return gspread.authorize(credentials).open_by_url(config["spreadsheet_url"]).worksheet(
        config["worksheet_name"].strip()
    )


def read_rows(sheet):
    values = sheet.get_all_values()
    if not values:
        return []
    if values[0] != HEADERS:
        raise ValueError("A primeira linha da aba deve conter: Referencia | Prateleira | Divisao. Use uma aba nova, exclusiva para este projeto.")
    records = []
    for number, row in enumerate(values[1:], start=2):
        if not any(row):
            continue
        if len(row) != 3:
            raise ValueError(f"Confira a linha {number}: ela deve ter três campos preenchidos.")
        reference, shelf, division = row
        clean = validate(reference, shelf, division)
        records.append(dict(zip(HEADERS, clean)))
    refs = [r["Referencia"].casefold() for r in records]
    if len(refs) != len(set(refs)):
        raise ValueError("Há referências repetidas na planilha. Mantenha uma localização por referência.")
    return records


def draw_shelf(shelf, records, matches):
    st.markdown(f"**{shelf}**")
    for letter in "AB":
        cells = []
        for division in [d for d in divisions(shelf) if d.startswith(letter)]:
            occupants = [r["Referencia"] for r in records if r["Prateleira"] == shelf and r["Divisao"] == division]
            highlighted = any(r["Prateleira"] == shelf and r["Divisao"] == division for r in matches)
            color = "#b45309" if highlighted else "#334155"
            title = html.escape(", ".join(occupants) or "Sem referências cadastradas", quote=True)
            cells.append(f'<div title="{title}" style="flex:1;text-align:center;border:1px solid #94a3b8;border-radius:4px;padding:8px 2px;background:{color};color:white"><b>{division}</b><br><small>{len(occupants)} ref.</small></div>')
        st.markdown('<div style="display:flex;gap:3px;margin-bottom:4px">' + "".join(cells) + "</div>", unsafe_allow_html=True)


st.title("🧵 Localizador de Tecidos")
st.caption("Encontre a prateleira e a divisão de cada referência.")
try:
    sheet = connect()
    records = read_rows(sheet)
except (KeyError, FileNotFoundError):
    st.info("Configure a conexão com o Google Sheets para começar. Siga o README.md e o modelo .streamlit/secrets.toml.example.")
    st.stop()
except Exception as error:
    st.error(f"Não foi possível carregar os dados ({type(error).__name__}). Confira a configuração, o compartilhamento e os cabeçalhos da aba.")
    if isinstance(error, ValueError):
        st.warning(str(error))
    st.stop()

if st.button("Atualizar dados da planilha"):
    st.rerun()

search_tab, register_tab, list_tab = st.tabs(["🔎 Buscar tecido", "➕ Cadastrar / alterar", "📋 Referências cadastradas"])
with search_tab:
    query = st.text_input("Referência do tecido", placeholder="Ex.: 80802825").strip()
    matches = [r for r in records if query.casefold() in r["Referencia"].casefold()] if query else []
    if query:
        if matches:
            for record in matches:
                st.success(f"Referência {record['Referencia']} → Prateleira {record['Prateleira']} · Divisão {record['Divisao']}")
        else:
            st.warning("Nenhuma referência encontrada.")
    st.subheader("Mapa das prateleiras")
    st.caption("A = parte de cima · B = parte de baixo. Os resultados da busca aparecem em laranja. A contagem em cada divisão indica referências cadastradas, não quantidade de tecido.")
    for group in [["P7", "P6", "P5", "P4", "P3", "P2", "P1"], ["P8", "P9"], ["P10", "P11", "P12", "P13", "P14"]]:
        columns = st.columns(len(group))
        for column, shelf in zip(columns, group):
            with column:
                draw_shelf(shelf, records, matches)
        st.write("")

with register_tab:
    st.caption("Uma localização por referência. Uma divisão pode guardar várias referências. Para mover um tecido, escolha alterar e selecione sua referência.")
    mode = st.radio("Operação", ["Cadastrar", "Alterar localização"], horizontal=True)
    if mode == "Alterar localização" and not records:
        st.info("Cadastre a primeira referência para poder alterar sua localização.")
    else:
        current = None
        if mode == "Alterar localização":
            reference = st.selectbox("Referência", sorted(r["Referencia"] for r in records))
            current = next(r for r in records if r["Referencia"] == reference)
        else:
            reference = st.text_input("Referência", key="new_reference")
        shelf = st.selectbox("Prateleira", SHELVES, index=SHELVES.index(current["Prateleira"]) if current else 0, key=f"shelf_{mode}_{reference if current else ''}")
        options = divisions(shelf)
        division = st.selectbox("Divisão", options, index=options.index(current["Divisao"]) if current and current["Divisao"] in options else 0, key=f"division_{mode}_{shelf}_{reference if current else ''}")
        if st.button("Salvar localização", type="primary"):
            try:
                row = validate(reference, shelf, division)
                latest = read_rows(sheet)
                existing = next((r for r in latest if r["Referencia"].casefold() == row[0].casefold()), None)
                if mode == "Cadastrar":
                    if existing:
                        raise ValueError("Essa referência já existe. Use Alterar localização.")
                    if not sheet.get_all_values():
                        sheet.update(range_name="A1:C1", values=[HEADERS], raw=True)
                    sheet.append_row(row, value_input_option="RAW", table_range="A:C")
                else:
                    if existing != current:
                        raise ValueError("Essa referência foi alterada na planilha. Atualize os dados antes de salvar.")
                    values = sheet.get_all_values()
                    positions = [i for i, value in enumerate(values[1:], start=2) if value and value[0].strip().casefold() == row[0].casefold()]
                    if len(positions) != 1:
                        raise ValueError("Referência ausente ou duplicada. Atualize os dados.")
                    number = positions[0]
                    sheet.update(range_name=f"A{number}:C{number}", values=[row], raw=True)
                st.session_state["saved_location"] = f"Referência {row[0]} salva em {row[1]} / {row[2]}."
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error("Não foi possível confirmar a gravação. Atualize os dados antes de tentar novamente.")
    if "saved_location" in st.session_state:
        st.success(st.session_state.pop("saved_location"))

with list_tab:
    selected = st.selectbox("Filtrar por prateleira", ["Todas"] + SHELVES)
    visible = [r for r in records if selected == "Todas" or r["Prateleira"] == selected]
    st.caption(f"{len(visible)} referência(s)")
    st.dataframe(visible, use_container_width=True, hide_index=True)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(records)
    st.download_button("Baixar cadastro completo (CSV)", output.getvalue().encode("utf-8-sig"), "referencias_tecidos.csv", "text/csv")
