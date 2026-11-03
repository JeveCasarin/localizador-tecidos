import csv
import html
import io

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from locations import HEADERS, SHELVES, validate, location_key

st.set_page_config(page_title="Localizador de Tecidos", page_icon="🧵", layout="centered")


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
    return records


def location_card(record):
    reference = html.escape(record["Referencia"])
    shelf = html.escape(record["Prateleira"])
    division = html.escape(record["Divisao"])
    position = "Parte de cima" if record["Divisao"].startswith("A") else "Parte de baixo"
    st.markdown(
        f'<div class="location-card"><div class="reference">Ref. {reference}</div>'
        f'<div class="location-values"><div>Prateleira<strong>{shelf}</strong></div>'
        f'<div>Divisão<strong>{division}</strong></div></div>'
        f'<div class="position">{position}</div></div>',
        unsafe_allow_html=True,
    )


st.markdown("""
<style>
.block-container {max-width: 720px; padding-top: 2rem; padding-bottom: 2rem;}
h1 {font-size: clamp(1.6rem, 6vw, 2.2rem) !important;}
.location-card {border: 1px solid #64748b; border-radius: 16px; padding: 20px; margin: 12px 0;}
.reference {font-size: 1.1rem; font-weight: 600; overflow-wrap: anywhere;}
.location-values {display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;}
.location-values strong {display: block; font-size: 2.3rem; line-height: 1.3;}
.position {margin-top: 12px; opacity: .75;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {min-height: 48px;}
@media (max-width: 600px) {
    .block-container {padding-left: 1rem; padding-right: 1rem;}
}
</style>
""", unsafe_allow_html=True)

st.title("🧵 Localizador de Tecidos")
st.caption("Encontre a prateleira e a divisão de cada referência.")
page = st.selectbox("O que deseja fazer?", ["🔎 Buscar tecido", "➕ Cadastrar / alterar", "📋 Referências cadastradas"])
if page != "➕ Cadastrar / alterar":
    st.caption("Atualização automática a cada 30 segundos enquanto esta tela estiver ativa.")


@st.fragment(run_every="30s" if page != "➕ Cadastrar / alterar" else None)
def render_page():
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

    if page == "🔎 Buscar tecido":
        query = st.text_input("Referência do tecido", placeholder="Ex.: 80802825").strip()
        matches = [r for r in records if query.casefold() in r["Referencia"].casefold()] if query else []
        if query:
            if matches:
                for record in matches:
                    location_card(record)
            else:
                st.warning("Nenhuma referência encontrada.")
        else:
            st.caption("Digite a referência e pressione Enter ou concluir no teclado do celular.")

    elif page == "➕ Cadastrar / alterar":
        st.caption("Uma referência pode estar em várias localizações. Cadastre cada localização separadamente. Para mover um tecido, altere somente a localização desejada.")
        mode = st.radio("Operação", ["Cadastrar", "Alterar localização"], horizontal=False)
        if mode == "Alterar localização" and not records:
            st.info("Cadastre a primeira referência para poder alterar sua localização.")
        else:
            current = None
            if mode == "Alterar localização":
                reference = st.text_input("Referência que deseja alterar", key="edit_reference").strip()
                candidates = [r for r in records if r["Referencia"].casefold() == reference.casefold()]
                if candidates:
                    current = st.radio("Qual localização deseja alterar?", candidates,
                        format_func=lambda r: f"{r['Prateleira']} / {r['Divisao']}")
                elif reference:
                    st.info("Referência não encontrada. Use Cadastrar para adicionar.")
            else:
                reference = st.text_input("Referência", key="new_reference")
            edit_key = "_".join(location_key(current)) if current else "new"
            shelf = st.text_input("Prateleira", value=current["Prateleira"] if current else "", placeholder="Ex.: p1", key=f"shelf_{mode}_{edit_key}")
            division = st.text_input("Divisão", value=current["Divisao"] if current else "", placeholder="Ex.: a1", key=f"division_{mode}_{edit_key}")
            st.caption("P1 e P2: A1–A4 ou B1–B4. P3 a P14: A1–A5 ou B1–B5.")
            if st.button("Salvar localização", type="primary", use_container_width=True, disabled=mode == "Alterar localização" and current is None):
                try:
                    row = validate(reference, shelf, division)
                    latest = read_rows(sheet)
                    target = dict(zip(HEADERS, row))
                    existing = next((r for r in latest if location_key(r) == location_key(target)), None)
                    if mode == "Cadastrar":
                        if existing:
                            raise ValueError("Essa referência já está cadastrada nessa prateleira e divisão. Informe outra localização.")
                        if not sheet.get_all_values():
                            sheet.update(range_name="A1:C1", values=[HEADERS], raw=True)
                        sheet.append_row(row, value_input_option="RAW", table_range="A:C")
                    else:
                        if existing and location_key(existing) != location_key(current):
                            raise ValueError("Essa referência já está cadastrada na localização de destino.")
                        values = sheet.get_all_values()
                        positions = [i for i, value in enumerate(values[1:], start=2)
                            if len(value) == 3 and location_key(dict(zip(HEADERS, validate(*value)))) == location_key(current)]
                        if len(positions) != 1:
                            raise ValueError("A localização original foi alterada ou está repetida na planilha. Atualize os dados e confira esse cadastro.")
                        number = positions[0]
                        sheet.update(range_name=f"A{number}:C{number}", values=[row], raw=True)
                    st.session_state["saved_location"] = f"Referência {row[0]} salva em {row[1]} / {row[2]}."
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
                except gspread.exceptions.APIError as error:
                    status = error.response.status_code
                    if status == 403:
                        st.error("O Google recusou a gravação (HTTP 403). Compartilhe a planilha com o client_email da conta de serviço como Editor e confira se a aba ou as células estão protegidas.")
                    elif status == 401:
                        st.error("Credencial recusada (HTTP 401). Confira a nova chave nos Secrets e reinicie o aplicativo.")
                    elif status == 429:
                        st.error("Limite temporário do Google Sheets (HTTP 429). Aguarde um minuto e atualize os dados antes de tentar novamente.")
                    else:
                        st.error(f"O Google Sheets retornou HTTP {status} ao salvar. Atualize os dados e confira se a referência foi gravada antes de repetir.")
                except Exception as error:
                    st.error(f"Não foi possível confirmar a gravação ({type(error).__name__}). Atualize os dados e confira se a referência foi gravada antes de repetir.")
        if "saved_location" in st.session_state:
            st.success(st.session_state.pop("saved_location"))

    elif page == "📋 Referências cadastradas":
        selected = st.selectbox("Filtrar por prateleira", ["Todas"] + SHELVES)
        visible = [r for r in records if selected == "Todas" or r["Prateleira"] == selected]
        st.caption(f"{len(visible)} referência(s)")
        if not visible:
            st.info("Nenhuma referência cadastrada nesta seleção.")
        for record in visible:
            location_card(record)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(records)
        st.download_button("Baixar cadastro completo (CSV)", output.getvalue().encode("utf-8-sig"), "referencias_tecidos.csv", "text/csv")



render_page()
