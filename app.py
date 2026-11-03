import csv
import html
import io

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from locations import HEADERS, SHELVES, validate, location_key

st.set_page_config(page_title="HOMEM.COM | Tecidos", page_icon="🧵", layout="centered")


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
        f'<div class="position">Prateleira {shelf[1:]} · {position} · Espaço {division[1:]}</div></div>',
        unsafe_allow_html=True,
    )


st.markdown("""
<style>
.block-container {max-width: 720px; padding-top: 2rem; padding-bottom: 2rem;}
h1 {font-size: clamp(1.6rem, 6vw, 2.2rem) !important;}
.location-card {border: 1px solid #cbd5e1; background: #ffffff; color: #172033; border-left: 5px solid #2563eb; border-radius: 16px; padding: 20px; margin: 12px 0;}
.reference {font-size: 1.1rem; font-weight: 600; overflow-wrap: anywhere;}
.location-values {display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;}
.location-values strong {display: block; font-size: 2.3rem; line-height: 1.3;}
.position {margin-top: 12px; color: #475569; font-size: .95rem;}
.brand-header {background: #1e1e1e; border-radius: 16px; padding: 20px; margin-bottom: 20px;}
.brand-header img {display: block; width: 201px; max-width: 100%; height: auto;}
.brand-header p {color: #cbd5e1; font-size: .85rem; margin: 10px 0 0;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {min-height: 48px;}
@media (max-width: 600px) {
    .block-container {padding-left: 1rem; padding-right: 1rem;}
}
</style>
""", unsafe_allow_html=True)

# Logo incorporada para não depender de um arquivo adicional no deploy.
LOGO = "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"
st.markdown(f'<header class="brand-header"><img src="data:image/png;base64,{LOGO}" alt="HOMEM.COM"><p>Localizador de tecidos</p></header>', unsafe_allow_html=True)
page = st.radio("Navegação", ["Buscar", "Cadastrar", "Cadastros"], horizontal=True, label_visibility="collapsed", key="navigation")
if page != "Cadastrar":
    st.caption("Dados atualizados automaticamente a cada 30 segundos.")


@st.fragment(run_every="30s" if page != "Cadastrar" else None)
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

    if page == "Buscar":
        st.title("Onde está o tecido?")
        st.caption("Busque a referência para encontrar todas as localizações.")
        with st.form("search_form"):
            typed_query = st.text_input("Referência do tecido", placeholder="Ex.: 10331", key="search_input")
            submitted = st.form_submit_button("Buscar tecido", type="primary", use_container_width=True)
        if submitted:
            st.session_state["active_query"] = typed_query.strip()
        query = st.session_state.get("active_query", "")
        matches = [r for r in records if query.casefold() in r["Referencia"].casefold()] if query else []
        if query:
            if matches:
                st.subheader(f"Encontrado em {len(matches)} {'local' if len(matches) == 1 else 'locais'}")
                for record in matches:
                    location_card(record)
            else:
                st.warning("Nenhuma referência encontrada.")
        else:
            st.caption("Informe a referência acima e toque em Buscar tecido.")

    elif page == "Cadastrar":
        st.title("Cadastrar localização")
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
                reference = st.text_input("Referência do tecido", placeholder="Ex.: 10331", key="new_reference")
            edit_key = "_".join(location_key(current)) if current else "new"
            shelf = st.text_input("Prateleira", value=current["Prateleira"] if current else "", placeholder="Ex.: p1", key=f"shelf_{mode}_{edit_key}")
            division = st.text_input("Divisão", value=current["Divisao"] if current else "", placeholder="Ex.: a1", key=f"division_{mode}_{edit_key}")
            st.caption("P1 e P2: A1–A4 ou B1–B4. P3 a P14: A1–A5 ou B1–B5.")
            if st.button("Salvar cadastro", type="primary", use_container_width=True, disabled=mode == "Alterar localização" and current is None):
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

    elif page == "Cadastros":
        st.title("Consultar cadastros")
        selected = st.selectbox("Filtrar por prateleira", ["Todas"] + SHELVES)
        visible = [r for r in records if selected == "Todas" or r["Prateleira"] == selected]
        st.caption(f"{len(visible)} localização(ões) cadastrada(s)")
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
