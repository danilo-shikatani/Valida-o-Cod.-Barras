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

    # Verifica se as colunas obrigatórias existem
    colunas_obrigatorias = ["cod.barras", "total", "forma pgto.", "filial", "no. titulo"]
    faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if faltando:
        st.error(f"O arquivo deve conter as colunas: {', '.join(faltando)}")
    else:
        # Renomeia para facilitar
        df = df.rename(columns={
            "cod.barras": "CodBarras",
            "total": "Total",
            "forma pgto.": "FormaPgto",
            "filial": "Filial",
            "no. titulo": "NoTitulo"
        })

        # Função de extração do valor do código de barras, variando por forma de pagamento
        def extrair_valor(codbarras, forma):
            try:
                codbarras = str(codbarras)
                if forma in ["30", "31"]:  # posições 09 a 19
                    valor_centavos = int(codbarras[9:19])
                elif forma in ["19", "91", "11", "13"]:  # posições 08 a 18
                    valor_centavos = int(codbarras[8:15])
                else:
                    return None
                return valor_centavos / 100
            except:
                return None

        df["Valor_CodBarras"] = df.apply(
            lambda x: extrair_valor(x["CodBarras"], str(x["FormaPgto"])),
            axis=1
        )

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
        df["Valor_Total_Titulo"] = df["Total"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df["Valor_CodBarras_Formatado"] = df["Valor_CodBarras"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notnull(x) else ""
        )
        df["Diferenca_ft"] = df["Diferenca"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

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
            df_filtrado[[
                "Filial",
                "NoTitulo",
                "FormaPgto",
                "CodBarras",
                "Valor_Total_Titulo",
                "Valor_CodBarras_Formatado",
                "Diferenca_ft",
                "Status"
            ]],
            use_container_width=True
        )

        # Download em Excel (com as colunas formatadas também)
        def to_excel(dataframe):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                dataframe.to_excel(writer, index=False, sheet_name="Validacao")
            return output.getvalue()

        excel_file = to_excel(
            df_filtrado[[
                "Filial",
                "NoTitulo",
                "FormaPgto",
                "CodBarras",
                "Valor_Total_Titulo",
                "Valor_CodBarras_Formatado",
                "Diferenca_ft",
                "Status"
            ]]
        )

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_file,
            file_name="boletos_validacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
