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


@st.cache_data(ttl=900, show_spinner=False)
def carregar_bases() -> tuple[pd.DataFrame, pd.DataFrame]:
    producao = pd.read_parquet(ARQ_PRODUCAO)
    metas = pd.read_excel(ARQ_METAS, sheet_name="METAS 2026")
    producao.columns = [str(c).strip() for c in producao.columns]
    metas.columns = [str(c).strip() for c in metas.columns]

    producao["DT_CONCLUSAO_DATA"] = pd.to_datetime(
        producao["DT_CONCLUSAO"], errors="coerce"
    )
    producao["ANO"] = pd.to_numeric(producao["ANO"], errors="coerce")
    producao["MES_NUM"] = pd.to_numeric(producao["MES_NUM"], errors="coerce")
    for coluna in INDICADORES + [
        "COM_IRREGULARIDADE", "SEM_IRREGULARIDADE", "NAO_EXECUTADO", "QTD_SS"
    ]:
        producao[coluna] = pd.to_numeric(
            producao.get(coluna, 0), errors="coerce"
        ).fillna(0)

    # A regional analítica é determinada exclusivamente pelo POLO.
    polo = producao["POLO"].fillna("").astype(str).str.upper()
    producao["REGIONAL_PAINEL"] = ""
    producao.loc[polo.str.contains("RIO VERDE"), "REGIONAL_PAINEL"] = "RIO VERDE"
    producao.loc[polo.str.contains("MORRINHOS"), "REGIONAL_PAINEL"] = "MORRINHOS"

    grupo = producao["GRUPOS"].fillna("").astype(str).str.upper()
    producao["GRUPO_PAINEL"] = ""
    producao.loc[grupo.str.startswith("A"), "GRUPO_PAINEL"] = "A"
    producao.loc[grupo.str.startswith("B"), "GRUPO_PAINEL"] = "B"

    metas.rename(columns={"MÊS": "MES"}, inplace=True)
    metas["REGIONAL"] = metas["REGIONAL"].map(normalizar_texto)
    metas["MES"] = metas["MES"].map(normalizar_texto)
    metas["GRUPO"] = metas["GRUPO"].map(normalizar_texto)
    metas["TIPO_NORMALIZADO"] = metas["TIPO DA META"].map(normalizar_texto)
    metas["QUANTIDADE"] = pd.to_numeric(metas["QUANTIDADE"], errors="coerce").fillna(0)
    return producao, metas


def familia_projeto(projeto: str) -> str | None:
    projeto_n = normalizar_texto(projeto)
    if projeto_n == "ALVO PROJETO":
        return "ALVO PROJETO"
    if projeto_n == "ALVO LEITURA":
        return "ALVO LEITURA"
    if projeto_n in {"VOL.DIREC.", "VOL DIREC", "VOLUNTARIO DIRECIONADO"}:
        return "VOLUNTARIO DIRECIONADO"
    if projeto_n == "VOLUNTARIO":
        return "VOLUNTARIO"
    if projeto_n == "CLANDESTINO":
        return "CLANDESTINO"
    return None


def obter_metas(
    metas: pd.DataFrame,
    regionais: list[str],
    grupos: list[str],
    meses_numeros: list[int],
    projetos: list[str],
) -> dict[str, float]:
    filtro = metas[
        metas["REGIONAL"].isin(regionais)
        & metas["GRUPO"].isin(grupos)
        & metas["MES"].isin([MESES[m] for m in meses_numeros])
    ].copy()

    familias = {familia_projeto(p) for p in projetos}
    familias.discard(None)
    usar_meta_projeto = len(familias) == 1 and len(projetos) == 1
    familia = next(iter(familias)) if usar_meta_projeto else None

    saida: dict[str, float] = {}
    for indicador in INDICADORES:
        prefixo = normalizar_texto(ROTULOS[indicador])
        if usar_meta_projeto:
            alvo = f"{prefixo} {familia}"
            linhas = filtro[filtro["TIPO_NORMALIZADO"].eq(alvo)]
        else:
            sufixos = ["AT" if g == "A" else "BT" for g in grupos]
            tipos = {f"{prefixo} {sufixo}" for sufixo in sufixos}
            # Corrige também a grafia FICALIZAÇÃO encontrada na planilha.
            if indicador == "FISCALIZACAO":
                tipos.add("FICALIZACAO BT")
                tipos.add("FICALIZACAO AT")
            linhas = filtro[filtro["TIPO_NORMALIZADO"].isin(tipos)]
        saida[indicador] = float(linhas["QUANTIDADE"].sum())
    return saida


def status_meta(real: float, meta: float) -> tuple[str, str]:
    if meta <= 0:
        return "Sem meta cadastrada", "neutro"
    percentual = real / meta
    if percentual >= 1:
        return "Meta atingida", "bom"
    if percentual >= 0.85:
        return "Próximo da meta", "atencao"
    return "Abaixo da meta", "critico"


def cartao_indicador(titulo: str, real: float, meta: float) -> None:
    percentual = real / meta * 100 if meta else 0
    status, classe = status_meta(real, meta)
    falta = max(meta - real, 0)
    st.markdown(
        f"""
        <div class="kpi-card {classe}">
          <div class="kpi-top"><span>{titulo}</span><span class="status">{status}</span></div>
          <div class="kpi-value">{real:,.0f}</div>
          <div class="kpi-meta">Meta {meta:,.0f} · {percentual:,.1f}%</div>
          <div class="track"><div class="fill" style="width:{min(percentual, 100):.1f}%"></div></div>
          <div class="kpi-foot">{"Superou em " + f"{real-meta:,.0f}" if real >= meta and meta else "Faltam " + f"{falta:,.0f}"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tema_figura(fig: go.Figure, altura: int = 390) -> go.Figure:
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CAD5E2", family="Inter, sans-serif"),
        margin=dict(l=12, r=12, t=92, b=28),
        title=dict(y=.98, x=.02, xanchor="left", yanchor="top"),
        legend=dict(
            orientation="h", y=1.03, x=0, yanchor="bottom", xanchor="left",
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#101D2E", font_color="white"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    return fig


st.markdown(
    """
    <style>
    .stApp {background: #07111F; color: #E8EEF6;}
    [data-testid="stSidebar"] {background: #0B1728; border-right: 1px solid #1E3047;}
    [data-testid="stHeader"] {background: rgba(7,17,31,.82);}
    h1, h2, h3 {letter-spacing: -.035em;}
    .block-container {padding-top: 1.6rem; max-width: 1550px;}
    .eyebrow {color:#38BDF8; font-size:.78rem; font-weight:800; letter-spacing:.14em;}
    .page-title {font-size:2.1rem; font-weight:800; margin:.18rem 0 0;}
    .subtitle {color:#8FA2B8; margin-bottom:1.1rem;}
    .kpi-card {
      background:linear-gradient(145deg,#101E30,#0C1828); border:1px solid #20334A;
      border-radius:16px; padding:1.05rem 1.1rem; min-height:185px;
      box-shadow:0 14px 35px rgba(0,0,0,.18);
    }
    .kpi-card.bom {border-top:3px solid #34D399;}
    .kpi-card.atencao {border-top:3px solid #FBBF24;}
    .kpi-card.critico {border-top:3px solid #FB7185;}
    .kpi-card.neutro {border-top:3px solid #64748B;}
    .kpi-top {display:flex; justify-content:space-between; gap:.5rem; color:#AFC0D2;
      text-transform:uppercase; font-size:.72rem; font-weight:800; letter-spacing:.07em;}
    .status {font-size:.64rem; padding:.18rem .42rem; background:#17283C; border-radius:99px;}
    .kpi-value {font-size:2.15rem; font-weight:850; margin:.65rem 0 .12rem;}
    .kpi-meta,.kpi-foot {font-size:.78rem; color:#8FA2B8;}
    .track {height:6px;background:#1C2D42;border-radius:99px;margin:.85rem 0 .55rem;overflow:hidden;}
    .fill {height:100%;background:linear-gradient(90deg,#0EA5E9,#34D399);border-radius:99px;}
    .mini-card {background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:1rem;}
    div[data-testid="stPlotlyChart"] {background:#0B1728;border:1px solid #1E3047;
      border-radius:16px;padding:.25rem .55rem;}
    div[data-testid="stDataFrame"] {border:1px solid #1E3047;border-radius:14px;overflow:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


try:
    producao, metas = carregar_bases()
except Exception as erro:
    st.error(f"Não foi possível carregar as bases: {erro}")
    st.stop()

producao = producao[producao["REGIONAL_PAINEL"].isin(["RIO VERDE", "MORRINHOS"])]
meses_disponiveis = sorted(producao["MES_NUM"].dropna().astype(int).unique().tolist())
if not meses_disponiveis:
    st.warning("Não há produção de Rio Verde ou Morrinhos na base.")
    st.stop()

with st.sidebar:
    st.markdown("### ⚡ Produção 2.0")
    st.caption("Recuperação de Energia · Sul")
    st.link_button("📊 Produção", "/", width="stretch")
    if PAGINA_CNR.is_file():
        st.page_link(
            "pages/2_Energia_CNR.py",
            label="Energia CNR",
            icon="⚡",
            width="stretch",
        )
    else:
        st.warning("Página CNR não encontrada em pages/2_Energia_CNR.py")
    st.markdown("---")
    regionais = st.multiselect(
        "Regional", ["RIO VERDE", "MORRINHOS"],
        default=["RIO VERDE", "MORRINHOS"],
    )
    mes = st.selectbox(
        "Mês de análise",
        meses_disponiveis,
        index=len(meses_disponiveis) - 1,
        format_func=lambda x: MESES[x].title(),
    )
    datas_mes = producao.loc[
        producao["MES_NUM"].eq(mes), "DT_CONCLUSAO_DATA"
    ].dropna()
    primeiro_dia_mes = pd.Timestamp(2026, mes, 1).date()
    ultimo_dia_mes = pd.Timestamp(2026, mes, monthrange(2026, mes)[1]).date()
    periodo = st.date_input(
        "Período por data",
        value=(primeiro_dia_mes, ultimo_dia_mes),
        min_value=primeiro_dia_mes,
        max_value=ultimo_dia_mes,
        format="DD/MM/YYYY",
    )
    grupos_disponiveis = ["A", "B"]
    grupos = st.multiselect("Grupo", grupos_disponiveis, default=grupos_disponiveis)

    base_opcoes = producao[
        producao["REGIONAL_PAINEL"].isin(regionais)
        & producao["MES_NUM"].eq(mes)
        & producao["GRUPO_PAINEL"].isin(grupos)
    ]
    opcoes_projeto = sorted(
        p for p in base_opcoes["projeto_perdas"].dropna().astype(str).unique() if p
    )
    projetos = st.multiselect("Projeto", opcoes_projeto, default=opcoes_projeto)
    opcoes_equipes = sorted(
        e for e in base_opcoes["PRX_DESCRICAO"].dropna().astype(str).unique() if e
    )
    equipes = st.multiselect("Equipe", opcoes_equipes, default=opcoes_equipes)
    st.markdown("---")
    if st.button("Atualizar leitura das bases", width="stretch"):
        st.cache_data.clear()
        st.rerun()

filtro = (
    producao["REGIONAL_PAINEL"].isin(regionais)
    & producao["MES_NUM"].eq(mes)
    & producao["GRUPO_PAINEL"].isin(grupos)
)
if isinstance(periodo, (tuple, list)):
    data_inicio = periodo[0]
    data_fim = periodo[-1] if len(periodo) > 1 else periodo[0]
else:
    data_inicio = data_fim = periodo
data_inicio_ts = pd.Timestamp(data_inicio)
data_fim_ts = pd.Timestamp(data_fim) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
filtro &= producao["DT_CONCLUSAO_DATA"].between(data_inicio_ts, data_fim_ts)
if projetos:
    filtro &= producao["projeto_perdas"].isin(projetos)
else:
    filtro &= False
if equipes:
    filtro &= producao["PRX_DESCRICAO"].isin(equipes)
else:
    filtro &= False
df = producao.loc[filtro].copy()

st.markdown('<div class="eyebrow">VISÃO DE PRODUÇÃO</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Desempenho operacional</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">{data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y} · '
    f'{", ".join(regionais) if regionais else "Nenhuma regional"} · '
    f'{len(df):,} registros filtrados</div>',
    unsafe_allow_html=True,
)

metas_mensais = obter_metas(metas, regionais, grupos, [mes], projetos)
dias_selecionados = (data_fim - data_inicio).days + 1
dias_no_mes = monthrange(2026, mes)[1]
fator_periodo = max(0, min(dias_selecionados / dias_no_mes, 1))
metas_filtro = {
    indicador: valor * fator_periodo
    for indicador, valor in metas_mensais.items()
}
realizados = {indicador: float(df[indicador].sum()) for indicador in INDICADORES}

colunas = st.columns(4)
for coluna_kpi, indicador in zip(colunas, INDICADORES):
    with coluna_kpi:
        cartao_indicador(ROTULOS[indicador], realizados[indicador], metas_filtro[indicador])

total_fisc = realizados["FISCALIZACAO"]
com_irreg = float(df["COM_IRREGULARIDADE"].sum())
sem_irreg = float(df["SEM_IRREGULARIDADE"].sum())
nao_exec = float(df["NAO_EXECUTADO"].sum())
assertividade = com_irreg / total_fisc * 100 if total_fisc else 0

st.markdown("### Qualidade da execução")
q1, q2, q3 = st.columns(3)
q1.metric("Assertividade", f"{assertividade:.1f}%", help="Com irregularidade ÷ fiscalizações")
q2.metric("Com irregularidade", f"{com_irreg:,.0f}")
q3.metric("Não executados", f"{nao_exec:,.0f}")

graf1, graf2 = st.columns([1.08, .92])
with graf1:
    comparativo = pd.DataFrame({
        "Indicador": [ROTULOS[i] for i in INDICADORES] * 2,
        "Tipo": ["Meta"] * 4 + ["Realizado"] * 4,
        "Quantidade": [metas_filtro[i] for i in INDICADORES]
        + [realizados[i] for i in INDICADORES],
    })
    fig = px.bar(
        comparativo, x="Indicador", y="Quantidade", color="Tipo", barmode="group",
        title="Meta x realizado",
        color_discrete_map={"Realizado": "#38BDF8", "Meta": "#52657B"},
        category_orders={"Tipo": ["Meta", "Realizado"]},
        text_auto=",.0f",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(tema_figura(fig), width="stretch")

with graf2:
    composicao = pd.DataFrame({
        "Resultado": ["Com irregularidade", "Sem irregularidade", "Não executado"],
        "Quantidade": [com_irreg, sem_irreg, nao_exec],
    })
    fig = px.pie(
        composicao, names="Resultado", values="Quantidade",
        title="Composição dos resultados", hole=.68,
        color="Resultado",
        color_discrete_map={
            "Com irregularidade": "#34D399",
            "Sem irregularidade": "#38BDF8",
            "Não executado": "#F87171",
        },
    )
    fig.update_traces(textinfo="percent+label+value")
    st.plotly_chart(tema_figura(fig), width="stretch")

df["DIA"] = df["DT_CONCLUSAO_DATA"].dt.day
diario = (
    df.groupby("DIA", as_index=False)[
        ["FISCALIZACAO", "FRAUDE", "COM_IRREGULARIDADE", "SEM_IRREGULARIDADE", "NAO_EXECUTADO"]
    ].sum()
)
if not diario.empty:
    diario["ASSERTIVIDADE"] = (
        diario["COM_IRREGULARIDADE"]
        .div(diario["FISCALIZACAO"].replace(0, pd.NA)).mul(100).fillna(0)
    )
    g1, g2 = st.columns([1.15, .85])
    with g1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=diario["DIA"], y=diario["FRAUDE"], name="Fraudes",
            mode="lines+markers+text", line=dict(color="#F59E0B", width=3),
            marker=dict(size=8), text=diario["FRAUDE"],
            texttemplate="%{text:,.0f}", textposition="top center",
        ))
        fig.update_layout(title="Evolução mensal de fraudes")
        st.plotly_chart(tema_figura(fig), width="stretch")
    with g2:
        fig = px.line(
            diario, x="DIA", y="ASSERTIVIDADE", markers=True,
            title="Assertividade diária",
        )
        fig.update_traces(line_color="#34D399", line_width=3)
        fig.update_traces(
            mode="lines+markers+text", text=diario["ASSERTIVIDADE"],
            texttemplate="%{text:.1f}%", textposition="top center"
        )
        fig.update_yaxes(ticksuffix="%", range=[0, max(100, diario["ASSERTIVIDADE"].max() * 1.15)])
        st.plotly_chart(tema_figura(fig), width="stretch")

equipe = (
    df.groupby("PRX_DESCRICAO", as_index=False)[INDICADORES]
    .sum().rename(columns={"PRX_DESCRICAO": "Equipe"})
)
if not equipe.empty:
    qtd_equipes = max(len(equipe), 1)
    posicoes = {
        "FISCALIZACAO": (1, 1), "NORMALIZACAO": (1, 2),
        "FRAUDE": (2, 1), "DEFEITO": (2, 2),
    }
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[ROTULOS[i] for i in INDICADORES],
        vertical_spacing=.18, horizontal_spacing=.09,
    )
    for indicador in INDICADORES:
        linha, coluna_grafico = posicoes[indicador]
        rotulo = ROTULOS[indicador]
        meta_por_equipe = metas_filtro[indicador] / qtd_equipes
        realizado_equipe = equipe[indicador].astype(float)
        cores_barras = [
            "#34D399" if meta_por_equipe > 0 and valor >= meta_por_equipe
            else CORES[rotulo]
            for valor in realizado_equipe
        ]
        situacoes = ["Meta atingida" if valor >= meta_por_equipe else "Abaixo da meta"
                     for valor in realizado_equipe]
        fig.add_trace(go.Bar(
            x=equipe["Equipe"],
            y=realizado_equipe,
            name=rotulo,
            marker_color=cores_barras,
            text=realizado_equipe,
            texttemplate="%{text:,.0f}", textposition="outside",
            customdata=situacoes,
            hovertemplate=(
                "Equipe: %{x}<br>Realizado: %{y:,.0f}<br>"
                f"Meta proporcional: {meta_por_equipe:,.1f}<br>"
                "Situação: %{customdata}<extra></extra>"
            ),
            showlegend=False,
        ), row=linha, col=coluna_grafico)
        fig.add_hline(
            y=meta_por_equipe, row=linha, col=coluna_grafico,
            line_color=CORES[rotulo], line_width=3, line_dash="dash",
            annotation_text=f"Meta {meta_por_equipe:,.0f}",
            annotation_position="top left",
            annotation_xshift=8,
            annotation_font_color=CORES[rotulo],
        )
        limite = max(float(realizado_equipe.max()), meta_por_equipe, 1) * 1.28
        fig.update_yaxes(range=[0, limite], row=linha, col=coluna_grafico)

    fig.update_layout(title="Produção por equipe", showlegend=False)
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(tema_figura(fig, 680), width="stretch")

c1, c2 = st.columns(2)
with c1:
    projetos_graf = (
        df.groupby("projeto_perdas", as_index=False)["FISCALIZACAO"].sum()
        .sort_values("FISCALIZACAO", ascending=True).tail(10)
    )
    fig = px.bar(
        projetos_graf, x="FISCALIZACAO", y="projeto_perdas", orientation="h",
        title="Fiscalizações por projeto", color_discrete_sequence=["#38BDF8"],
        text="FISCALIZACAO",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema_figura(fig), width="stretch")
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
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema_figura(fig), width="stretch")

with st.expander("Consultar produção detalhada"):
    colunas_tabela = [
        "NR_OS", "DT_CONCLUSAO", "REGIONAL_PAINEL", "GRUPOS",
        "PRX_DESCRICAO", "EMP_SIGLA", "projeto_perdas",
        "RESULTADO_INSPECAO_1", "CODIGO_IRREGULARIDADE_CAMPO",
        "NOME_MUNICIPIO", "UC",
    ]
    colunas_tabela = [c for c in colunas_tabela if c in df.columns]
    detalhe = df[colunas_tabela].sort_values("DT_CONCLUSAO", ascending=False)
    st.dataframe(detalhe, width="stretch", hide_index=True, height=430)
    st.download_button(
        "Baixar seleção em CSV",
        detalhe.to_csv(index=False, sep=";", encoding="utf-8-sig"),
        file_name=f"producao_{MESES[mes].lower()}_2026.csv",
        mime="text/csv",
    )

horario_atualizacao = datetime.fromtimestamp(
    ARQ_PRODUCAO.stat().st_mtime,
    tz=ZoneInfo("America/Sao_Paulo"),
)
st.caption(
    f"Dados atualizados em: {horario_atualizacao:%d/%m/%Y às %H:%M} · "
    "Fonte: ODS de produção · Data de referência: DT_CONCLUSAO · "
    "Rio Verde e Morrinhos definidos pela coluna POLO."
)
