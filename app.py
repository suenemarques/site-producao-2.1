from __future__ import annotations

import re
import unicodedata
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from auth_site import acesso_geral, exigir_login, filtrar_por_acesso


st.set_page_config(
    page_title="Produção 2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
ARQ_PRODUCAO = BASE_DIR / "dados" / "producao_2026.parquet"
ARQ_METAS = BASE_DIR / "METAS 2026.xlsx"
PAGINA_CNR = BASE_DIR / "pages" / "2_Energia_CNR.py"
PAGINA_INCREMENTO = BASE_DIR / "pages" / "3_Incremento.py"

MESES = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}
INDICADORES = ["FISCALIZACAO", "NORMALIZACAO", "FRAUDE", "DEFEITO"]
ROTULOS = {
    "FISCALIZACAO": "Fiscalização",
    "NORMALIZACAO": "Normalização",
    "FRAUDE": "Fraude",
    "DEFEITO": "Defeito",
}
CORES = {
    "Fiscalização": "#38BDF8",
    "Normalização": "#34D399",
    "Fraude": "#F59E0B",
    "Defeito": "#F87171",
}


def normalizar_texto(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def normalizar_servico(valor: object) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", normalizar_texto(valor)).strip()


def formatar_duracao(inicio: pd.Series, fim: pd.Series) -> pd.Series:
    """Retorna a diferença entre duas datas no formato HH:MM:SS."""
    segundos = (fim - inicio).dt.total_seconds()
    resultado = pd.Series("", index=inicio.index, dtype="object")
    validos = segundos.notna() & segundos.ge(0)

    def para_hhmmss(valor: float) -> str:
        total = int(valor)
        horas, resto = divmod(total, 3600)
        minutos, segundos_restantes = divmod(resto, 60)
        return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d}"

    resultado.loc[validos] = segundos.loc[validos].map(para_hhmmss)
    return resultado


def categorizar_servico_grupo_a(descricao: object, resultado: object) -> str:
    servico = normalizar_servico(descricao)
    resultado_n = normalizar_servico(resultado)
    fiscalizacao = {"INSPECOES", "INSPECAO PERDAS AT BI OPAT"}
    telemetria = {"MANUTENCAO CENTRO DE MEDICAO", "MANUTENCAO DE TELEMETRIA GRUPO A", "MANUTENCAO DE FRONTEIRA"}
    anexo_comercial = {
        "DESLIGAMENTO LIGACAO PROVISORIA GRUPO A", "CONEXAO GD GRUPO A",
        "CONEXAO GD GRUPO A OLD PROCESS", "CONEXAO GD MICROGERACAO",
        "DESLIGAMENTO DE UC GRUPO A", "DESLIGAMENTO DE UC GRUPO A A PEDIDO DA DISTRIBUIDORA",
        "DESLIGAMENTO LIGACAO PROVISORIA", "INSPECAO DE UC GRUPO A",
        "LIGACAO NOVA CAMPO RURAL 10 DIAS", "LIGACAO NOVA CAMPO URBANA 10 DIAS",
        "LIGACAO NOVA CAMPO URBANA", "LIGACAO NOVA CAMPO RURAL", "LIGACAO NOVA GRUPO A",
        "LIGACAO NOVA RURAL GRUPO A", "LIGACAO NOVA URBANA GRUPO A",
        "LIGACAO NOVA GRUPO A CAMPO RURAL 10 DIAS", "LIGACAO PROVISORIA GRUPO A",
        "MUDANCA DE PADRAO AUMENTO DE CARGA GR A", "REATIVACAO DE UC GRUPO A",
        "REATIVACAO DE UC GER DIST GRUPO A", "FORNECIMENTO DE PULSO E SINCRONISMO",
        "INSTALACAO DE TELEMETRIA GRUPO A", "LEITURA EM CAMPO GRUPO A",
        "MEDICAO DE QUALIDADE POR AMOSTRAL ANEEL GRUPO A",
with c2:
    motivos = (
        df.loc[df["NAO_EXECUTADO"].gt(0), "MOTIVO_NAO_EXECUTADO"]
        .fillna("Não informado").replace("", "Não informado")
        .value_counts().head(10).rename_axis("Motivo").reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )
    fig = px.bar(
        motivos, x="Quantidade", y="Motivo", orientation="h",
        title="Principais motivos de não execução",
        color_discrete_sequence=["#F87171"],
        text="Quantidade",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema_figura(fig), width="stretch")

with st.expander("Consultar produção detalhada"):
    detalhe_base = df.copy()
    campos_datahora = {
        "HOST_VI_DT_INI_DESLOCAMENTO": "HORARIO_INICIO_DESLOCAMENTO",
        "HOST_VI_DT_FIM_DESLOCAMENTO": "HORARIO_FIM_DESLOCAMENTO",
        "HOST_VI_DT_INI_SERVICO": "HORARIO_INICIO_SERVICO",
        "HOST_VI_DT_FIM_SERVICO": "HORARIO_FIM_SERVICO",
    }
    datas_convertidas = {}
    for coluna_origem, coluna_horario in campos_datahora.items():
        if coluna_origem in detalhe_base.columns:
            datas_convertidas[coluna_origem] = pd.to_datetime(
                detalhe_base[coluna_origem], errors="coerce", dayfirst=True
            )
            detalhe_base[coluna_horario] = datas_convertidas[
                coluna_origem
            ].dt.strftime("%H:%M:%S").fillna("")
        else:
            datas_convertidas[coluna_origem] = pd.Series(
                pd.NaT, index=detalhe_base.index, dtype="datetime64[ns]"
            )
            detalhe_base[coluna_horario] = ""

    detalhe_base["TEMPO_DESLOCAMENTO"] = formatar_duracao(
        datas_convertidas["HOST_VI_DT_INI_DESLOCAMENTO"],
        datas_convertidas["HOST_VI_DT_FIM_DESLOCAMENTO"],
    )
    detalhe_base["TEMPO_SERVICO"] = formatar_duracao(
        datas_convertidas["HOST_VI_DT_INI_SERVICO"],
        datas_convertidas["HOST_VI_DT_FIM_SERVICO"],
    )

    colunas_tabela = [
        "NR_OS", "DT_CONCLUSAO", "REGIONAL_PAINEL", "GRUPOS",
        "PRX_DESCRICAO", "EMP_SIGLA", "projeto_perdas",
        "RESULTADO_INSPECAO_1", "CODIGO_IRREGULARIDADE_CAMPO",
        "MOTIVO_NAO_EXECUTADO", "NOME_MUNICIPIO", "UC",
        "HORARIO_INICIO_DESLOCAMENTO", "HORARIO_FIM_DESLOCAMENTO",
        "TEMPO_DESLOCAMENTO", "HORARIO_INICIO_SERVICO",
        "HORARIO_FIM_SERVICO", "TEMPO_SERVICO",
    ]
    colunas_tabela = [c for c in colunas_tabela if c in detalhe_base.columns]
    detalhe = detalhe_base[colunas_tabela].sort_values(
        "DT_CONCLUSAO", ascending=False
    )
    detalhe = detalhe.rename(columns={
        "HORARIO_INICIO_DESLOCAMENTO": "Horário início deslocamento",
        "HORARIO_FIM_DESLOCAMENTO": "Horário fim deslocamento",
        "TEMPO_DESLOCAMENTO": "Tempo deslocamento",
        "HORARIO_INICIO_SERVICO": "Horário início serviço",
        "HORARIO_FIM_SERVICO": "Horário fim serviço",
        "TEMPO_SERVICO": "Tempo serviço",
    })
    st.dataframe(detalhe, width="stretch", hide_index=True, height=430)
    st.download_button(
        "Baixar seleção em CSV",
        detalhe.to_csv(index=False, sep=";", encoding="utf-8-sig"),
        file_name=(
            f"producao_{meses[0]:02d}_a_{meses[-1]:02d}_2026.csv"
            if len(meses) > 1
            else f"producao_{MESES[meses[0]].lower()}_2026.csv"
        ),
        mime="text/csv",
    )

horario_atualizacao = None
if "ATUALIZADO_EM" in producao.columns:
    horarios_base = pd.to_datetime(
        producao["ATUALIZADO_EM"], errors="coerce", utc=True
    ).dropna()
    if not horarios_base.empty:
        horario_atualizacao = horarios_base.max().tz_convert(
            "America/Sao_Paulo"
        ).to_pydatetime()

# O arquivo pode ter sido substituído no GitHub/Streamlit mesmo quando uma
# versão antiga da coluna ATUALIZADO_EM permaneceu dentro do parquet. Nesse
# caso, considera também a modificação real do arquivo e mostra a data mais
# recente entre as duas fontes.
horario_arquivo = datetime.fromtimestamp(
    ARQ_PRODUCAO.stat().st_mtime,
    tz=ZoneInfo("America/Sao_Paulo"),
)
if horario_atualizacao is None or horario_arquivo > horario_atualizacao:
    horario_atualizacao = horario_arquivo

st.caption(
    f"Dados atualizados em: {horario_atualizacao:%d/%m/%Y às %H:%M} · "
    "Fonte: ODS de produção · Data de referência: DT_CONCLUSAO · "
    "Rio Verde e Morrinhos definidos pela coluna POLO."
)
