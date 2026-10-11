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

from auth_site import exigir_login, filtrar_por_acesso


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


def normalizar_regional(valor: object) -> str:
    # Une nomes da ODS (05.Iporá/06.Montes Belos) e do Excel de metas.
    texto = normalizar_texto(valor)
    texto = re.sub(r"^\d+\s*[.\-]?\s*", "", texto).strip()
    nomes = {"RIO VERDE", "MORRINHOS", "IPORA", "MONTES BELOS"}
    return texto if texto in nomes else ""


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
