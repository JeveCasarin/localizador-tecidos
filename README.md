# Localizador de Tecidos

Aplicativo Streamlit com Google Sheets para buscar referências por prateleira e divisão. Não controla quantidade de estoque.

## Regras

- P1 e P2: A1–A4 e B1–B4.
- P3 a P14: A1–A5 e B1–B5.
- A significa parte de cima; B significa parte de baixo.
- Uma localização por referência; várias referências podem compartilhar uma divisão.
- Busca parcial, cadastro, alteração de localização, mapa conforme o desenho e exportação CSV.
- Referências são texto, preservando zeros à esquerda. Ao editar diretamente no Sheets, formate a coluna A como Texto simples antes de digitar.
- As gravações adicionam uma linha ou atualizam apenas a linha escolhida, sem apagar a aba.

## 1. Criar o novo repositório no GitHub

1. Entre no GitHub e clique em **+ → New repository**.
2. Sugestão de nome: `localizador-tecidos`. Escolha a visibilidade desejada e clique em **Create repository**.
3. Use **uploading an existing file** ou **Add file → Upload files**.
4. Envie `app.py`, `locations.py`, `requirements.txt`, `README.md` e `.gitignore`. Clique em **Commit changes**.
5. O arquivo `.streamlit/secrets.toml.example` é somente um modelo local. Não envie chaves privadas nem o arquivo real `secrets.toml` ao GitHub.

## 2. Preparar uma planilha nova

1. Crie uma planilha Google separada da planilha de estoque antiga.
2. Renomeie a aba para `Referencias`.
3. Na primeira linha, preencha exatamente: A1 `Referencia`, B1 `Prateleira`, C1 `Divisao`.
4. Selecione a coluna A e use **Formatar → Número → Texto simples**.
5. Opcionalmente, cadastre uma linha de exemplo: `80802825`, `P6`, `A4`.

## 3. Dar acesso ao aplicativo

Se já possui a conta de serviço usada no aplicativo antigo, você pode reutilizá-la e compartilhar a nova planilha com seu `client_email`, com permissão de Editor.

Se precisar criar uma conta:

1. Abra o Google Cloud Console e crie ou selecione um projeto.
2. Em **APIs e serviços → Biblioteca**, ative a **Google Sheets API**.
3. Em **IAM e administrador → Contas de serviço**, crie uma conta de serviço.
4. Abra a conta criada, vá em **Chaves → Adicionar chave → Criar nova chave → JSON**.
5. Guarde o arquivo em local privado. Compartilhe a planilha com o endereço `client_email` desse arquivo como Editor.

## 4. Publicar no Streamlit

1. Entre em https://share.streamlit.io e conecte sua conta GitHub.
2. Crie um aplicativo, selecione o novo repositório e informe `app.py` como arquivo principal.
3. Em **Advanced settings → Secrets**, cole o modelo de `.streamlit/secrets.toml.example`.
4. Substitua a URL e o nome da aba. Preencha os campos da conta de serviço com os valores do JSON. Preserve os `\n` da chave privada dentro das aspas.
5. Clique em **Deploy**. Depois, os segredos podem ser ajustados nas configurações do aplicativo.

Documentação: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## 5. Conferir o funcionamento

1. Cadastre `80802825` em P6 / A4 e pesquise essa referência.
2. Confira o resultado e o destaque laranja no mapa.
3. Selecione P1 e P2 no cadastro: A5 e B5 não devem aparecer.
4. Cadastre `00123` e confira se os zeros são mantidos.
5. Use **Alterar localização** para mover uma referência e repita a busca.

## Executar no computador (opcional)

Instale Python 3.11 ou superior. Abra um terminal nesta pasta e execute:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Preencha `.streamlit/secrets.toml` com a configuração real e execute:

```powershell
.venv\Scripts\python -m streamlit run app.py
```

## Limites desta primeira versão

A integração real precisa ser conferida depois de configurar a planilha. A aplicação não possui login: quem tiver acesso ao aplicativo poderá cadastrar e alterar referências. Defina o acesso ao aplicativo antes de disponibilizá-lo para outras pessoas. Google Sheets não oferece transações nesta implementação; evite edições simultâneas da mesma referência e alterações manuais de linhas durante gravações. O CSV contém o cadastro completo, mas ainda não há importação automática de backup nem exclusão pela interface.
