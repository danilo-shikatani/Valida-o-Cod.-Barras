import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Validador de Boletos", layout="wide")

st.title("🔎 Validador de Boletos - Linha Digitável x Valor Total")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload do arquivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    # Carregar planilha
    df = pd.read_excel(uploaded_file)

    # Normaliza nomes de colunas (remove espaços, maiúscula/minúscula)
    df.columns = df.columns.str.strip().str.lower()

    # Verifica se as colunas existem
    if "cod.barras" not in df.columns or "total" not in df.columns or "forma pgto." not in df.columns:
        st.error("O arquivo deve conter as colunas 'Cod.Barras', 'Total' e 'Forma Pgto.'.")
    else:
        # Renomeia para facilitar
        df = df.rename(columns={
            "cod.barras": "CodBarras",
            "total": "Total",
            "forma pgto.": "FormaPgto"
        })


        # Extrair valor do código de barras (posição 10 a 18)
        def extrair_valor(codbarras):
            try:
                valor_centavos = int(str(codbarras)[9:19])  # índice começa em 0
                return valor_centavos / 100  # converte para reais
            except:
                return None

        df["Valor_CodBarras"] = df["CodBarras"].astype(str).apply(extrair_valor)

        # Diferença
        df["Diferenca"] = df["Total"] - df["Valor_CodBarras"]

        # Comparação
        df["Status"] = df.apply(
            lambda x: "OK" if round(x["Total"], 2) == round(x["Valor_CodBarras"], 2) else "Divergente",
            axis=1,
        )

        # Filtro de Forma de Pagamento (somente 30, 31, 19, 91, 11)
        formas_validas = ["30", "31", "19", "91", "11"]
        df = df[df["FormaPgto"].astype(str).isin(formas_validas)]

        # Criar colunas formatadas para exibição
        df["Total_Formatado"] = df["Total"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        df["Valor_CodBarras_Formatado"] = df["Valor_CodBarras"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else "")
        df["Diferenca_Formatada"] = df["Diferenca"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Filtro de status
        filtro = st.radio("Filtrar resultados:", ["Todos", "Somente Divergentes", "Somente OK"])
        if filtro == "Somente Divergentes":
            df_filtrado = df[df["Status"] == "Divergente"]
        elif filtro == "Somente OK":
            df_filtrado = df[df["Status"] == "OK"]
        else:
            df_filtrado = df.copy()

        # Mostrar só colunas relevantes já formatadas
        st.dataframe(
            df_filtrado[["FormaPgto", "CodBarras", "Total_Formatado", "Valor_CodBarras_Formatado", "Diferenca_Formatada", "Status"]],
            use_container_width=True
        )

        # Download em Excel (com as colunas formatadas também)
        def to_excel(dataframe):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                dataframe.to_excel(writer, index=False, sheet_name="Validacao")
            return output.getvalue()

        excel_file = to_excel(df_filtrado[["FormaPgto", "CodBarras", "Total_Formatado", "Valor_CodBarras_Formatado", "Diferenca_Formatada", "Status"]])

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_file,
            file_name="boletos_validacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
