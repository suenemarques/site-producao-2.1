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
REGIONAIS_PAINEL = ["MORRINHOS", "RIO VERDE", "IPORA", "MONTES BELOS"]
ROTULOS_REGIONAIS = {
    "MORRINHOS": "03.Morrinhos", "RIO VERDE": "04.Rio Verde",
    "IPORA": "05.Iporá", "MONTES BELOS": "06.Montes Belos",
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
    texto = normalizar_texto(valor)
    texto = re.sub(r"^\d+\s*[.\-]?\s*", "", texto)
    texto = re.sub(r"[^A-Z0-9]+", " ", texto).strip()
    for nome in REGIONAIS_PAINEL:
        if re.search(r"(?:^| )" + re.escape(nome) + r"(?: |$)", texto):
            return nome
    return ""


def classificar_regionais(producao: pd.DataFrame) -> pd.Series:
    resultado = pd.Series("", index=producao.index, dtype=str)
    # A REGIONAL da ODS reconhece as novas regionais mesmo com POLO diferente.
    # Campos preparados pelo atualizador e POLO são alternativas para vazios.
    for nome_coluna in ["REGIONAL", "REGIONAL_SITE", "POLO"]:
        if nome_coluna in producao.columns:
            identificada = producao[nome_coluna].map(normalizar_regional)
            resultado = resultado.where(resultado.ne(""), identificada)
    return resultado


def mes_meta_normalizado(valor: object) -> str:
    texto = normalizar_texto(valor)
    try:
        numero = float(texto.replace(",", "."))
        if numero.is_integer() and 1 <= numero <= 12:
            return normalizar_texto(MESES[int(numero)])
    except ValueError:
        pass
    for numero, nome in MESES.items():
        nome_n = normalizar_texto(nome)
        if texto == nome_n or texto == nome_n[:3]:
            return nome_n
