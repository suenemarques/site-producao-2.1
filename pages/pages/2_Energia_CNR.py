from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Energia CNR", page_icon="⚡", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[1]
ARQ_CNR = BASE_DIR / "dados" / "cnr_2026.parquet"
ARQ_METAS = BASE_DIR / "METAS 2026.xlsx"
MESES = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}
CORES_STATUS = {
    "Faturada": "#34D399", "Cancelamento": "#F59E0B",
    "Cancelamento Estratégico": "#F87171", "Outro": "#64748B",
}


def normalizar(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def rotulo_status(valor: object) -> str:
    status = normalizar(valor)
    if status.startswith("1") or "FATUR" in status:
        return "Faturada"
    if status.startswith("3") or "ESTRATEG" in status:
        return "Cancelamento Estratégico"
    if status.startswith("2") or "CANCELAMENTO" in status:
        return "Cancelamento"
    return "Outro"


@st.cache_data(ttl=900, show_spinner=False)
def carregar() -> tuple[pd.DataFrame, pd.DataFrame]:
    cnr = pd.read_parquet(ARQ_CNR)
    cnr.columns = [str(c).strip() for c in cnr.columns]
    cnr["CNR_ENERGIA"] = pd.to_numeric(cnr["CNR_ENERGIA"], errors="coerce").fillna(0)
    cnr["FISCAL_CICLO_STATUS_ANO"] = pd.to_numeric(
        cnr["FISCAL_CICLO_STATUS_ANO"], errors="coerce"
    ).astype("Int64")
    cnr["FISCAL_CICLO_STATUS_MES"] = pd.to_numeric(
        cnr["FISCAL_CICLO_STATUS_MES"], errors="coerce"
    ).astype("Int64")
    cnr["REGIONAL"] = cnr["NOVA_REGIONAL"].map(normalizar)
    cnr["GRUPO"] = cnr["GRUPO_CNR"].map(normalizar)
    cnr["STATUS_ROTULO"] = cnr["STATUS_CNR_EQTL"].map(rotulo_status)
    cnr["PROJETO"] = cnr["PROJETO_PERDA"].fillna("Não informado").replace("", "Não informado")
    cnr["IRREGULARIDADE"] = cnr["TIPO_IRREGULARIDADE_TOI"].fillna("Não informado").replace("", "Não informado")
    cnr["LIGACAO"] = cnr["TIPOLIGACAO"].fillna("Não informado").replace("", "Não informado")
    cnr["MOTIVO"] = cnr["MOTIVO_CANCELAMENTO_DESCRICAO"].fillna("Não informado").replace("", "Não informado")
    cnr["MES_NOME"] = cnr["FISCAL_CICLO_STATUS_MES"].map(MESES)

    metas = pd.read_excel(ARQ_METAS, sheet_name="METAS 2026")
    metas.columns = [str(c).strip() for c in metas.columns]
    metas.rename(columns={"MÊS": "MES"}, inplace=True)
    for coluna in ["REGIONAL", "MES", "GRUPO", "TIPO DA META"]:
        if coluna not in metas.columns:
            metas[coluna] = ""
        metas[coluna] = metas[coluna].map(normalizar)
    metas["QUANTIDADE"] = pd.to_numeric(metas.get("QUANTIDADE", 0), errors="coerce").fillna(0)
    return cnr, metas


def meta_cnr(metas: pd.DataFrame, regionais: list[str], grupos: list[str], meses: list[int]) -> dict[str, float]:
    base = metas[
        metas["REGIONAL"].isin(regionais)
        & metas["MES"].isin([MESES[m] for m in meses])
        & metas["TIPO DA META"].str.contains("CNR", na=False)
    ].copy()
    resultado: dict[str, float] = {}
    for grupo in grupos:
        por_coluna = base[base["GRUPO"].eq(grupo)]
        if grupo == "IP":
            por_tipo = base[base["TIPO DA META"].str.contains(r"\bIP\b", regex=True, na=False)]
        elif grupo == "A":
            por_tipo = base[base["TIPO DA META"].str.contains(r"\bAT\b|GRUPO A", regex=True, na=False)]
        else:
            por_tipo = base[base["TIPO DA META"].str.contains(r"\bBT\b|GRUPO B", regex=True, na=False)]
        linhas = por_coluna if not por_coluna.empty else por_tipo
        resultado[grupo] = float(linhas["QUANTIDADE"].sum())
    return resultado


def tema(fig, altura: int = 390):
    fig.update_layout(
        height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CAD5E2", family="Inter, sans-serif"),
        margin=dict(l=15, r=20, t=90, b=35),
        title=dict(y=.98, x=.02, xanchor="left", yanchor="top"),
        legend=dict(orientation="h", y=1.03, x=0, yanchor="bottom"),
        hoverlabel=dict(bgcolor="#101D2E", font_color="white"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    return fig


def moeda_energia(valor: float) -> str:
    return f"{valor:,.0f} kWh"


st.markdown("""
<style>
.stApp {background:#07111F;color:#E8EEF6}
[data-testid="stSidebar"] {background:#0B1728;border-right:1px solid #1E3047}
.block-container {padding-top:1.5rem;max-width:1550px}
.eyebrow {color:#38BDF8;font-size:.78rem;font-weight:800;letter-spacing:.14em}
.page-title {font-size:2.1rem;font-weight:800;margin:.18rem 0 0}
.subtitle {color:#8FA2B8;margin-bottom:1rem}
div[data-testid="stPlotlyChart"] {background:#0B1728;border:1px solid #1E3047;border-radius:16px;padding:.25rem .55rem}
div[data-testid="stMetric"] {background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:1rem}
</style>
""", unsafe_allow_html=True)

try:
    cnr, metas = carregar()
except Exception as erro:
    st.error(f"Não foi possível carregar a base de CNR: {erro}")
    st.info("Execute primeiro o atualizador para gerar dados/cnr_2026.parquet.")
    st.stop()

with st.sidebar:
    st.markdown("### ⚡ Energia CNR")
    st.caption("Recuperação de Energia · Sul")
    st.markdown("---")
    regionais_disp = [r for r in ["03.MORRINHOS", "04.RIO VERDE"] if r in set(cnr["REGIONAL"])]
    regionais = st.multiselect("Regional", regionais_disp, default=regionais_disp)
    grupos_disp = [g for g in ["A", "B", "IP"] if g in set(cnr["GRUPO"])]
    grupos = st.multiselect("Grupo CNR", grupos_disp, default=grupos_disp)
    meses_disp = sorted(cnr["FISCAL_CICLO_STATUS_MES"].dropna().astype(int).unique())
    meses = st.multiselect("Mês do status", meses_disp, default=list(meses_disp), format_func=lambda m: MESES[m].title())
    status_disp = [s for s in CORES_STATUS if s in set(cnr["STATUS_ROTULO"])]
    status = st.multiselect("Status", status_disp, default=status_disp)
    projetos_disp = sorted(cnr["PROJETO"].astype(str).unique())
    projetos = st.multiselect("Projeto", projetos_disp, default=projetos_disp)
    irregularidades_disp = sorted(cnr["IRREGULARIDADE"].astype(str).unique())
    irregularidades = st.multiselect("Irregularidade", irregularidades_disp, default=irregularidades_disp)
    ligacoes_disp = sorted(cnr["LIGACAO"].astype(str).unique())
    ligacoes = st.multiselect("Tipo de ligação", ligacoes_disp, default=ligacoes_disp)
    st.markdown("---")
    if st.button("Atualizar leitura das bases", width="stretch"):
        st.cache_data.clear()
        st.rerun()

filtro = (
    cnr["REGIONAL"].isin(regionais) & cnr["GRUPO"].isin(grupos)
    & cnr["FISCAL_CICLO_STATUS_MES"].isin(meses) & cnr["STATUS_ROTULO"].isin(status)
    & cnr["PROJETO"].isin(projetos) & cnr["IRREGULARIDADE"].isin(irregularidades)
    & cnr["LIGACAO"].isin(ligacoes)
)
df = cnr.loc[filtro].copy()
real = df[df["STATUS_ROTULO"].isin(["Faturada", "Cancelamento"])].copy()
cancelados = df[df["STATUS_ROTULO"].isin(["Cancelamento", "Cancelamento Estratégico"])].copy()

st.markdown('<div class="eyebrow">VISÃO ENERGÉTICA</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Energia CNR</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">2026 · {len(df):,} registros filtrados · '
    f'{", ".join(regionais) if regionais else "Nenhuma regional"}</div>', unsafe_allow_html=True
)

if not cancelados.empty:
    ultimo_mes_cancelado = int(cancelados["FISCAL_CICLO_STATUS_MES"].max())
    recentes = cancelados[cancelados["FISCAL_CICLO_STATUS_MES"].eq(ultimo_mes_cancelado)]
    st.warning(
        f"⚠️ Alerta de cancelamento: {recentes['INSPECAO_ID'].nunique():,.0f} SS e "
        f"{recentes['CNR_ENERGIA'].sum():,.0f} kWh cancelados em {MESES[ultimo_mes_cancelado].title()}."
    )
    with st.expander("Ver cancelamentos do alerta"):
        st.dataframe(
            recentes[["INSPECAO_ID", "NOVA_REGIONAL", "GRUPO_CNR", "STATUS_CNR_EQTL",
                      "CNR_ENERGIA", "MOTIVO_CANCELAMENTO_DESCRICAO", "PROJETO_PERDA"]]
            .sort_values("CNR_ENERGIA", ascending=False),
            width="stretch", hide_index=True,
        )

metas_grupo = meta_cnr(metas, regionais, grupos, meses)
meta_total = sum(metas_grupo.values())
energia_real = float(real["CNR_ENERGIA"].sum())
qtd_processos = int(df["INSPECAO_ID"].nunique())
qtd_cancelados = int(cancelados["INSPECAO_ID"].nunique())
ticket = energia_real / real["INSPECAO_ID"].nunique() if real["INSPECAO_ID"].nunique() else 0
taxa_cancelamento = qtd_cancelados / qtd_processos * 100 if qtd_processos else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Real CNR", moeda_energia(energia_real))
k2.metric("Meta CNR", moeda_energia(meta_total))
k3.metric("Atingimento", f"{energia_real / meta_total * 100:.1f}%" if meta_total else "Sem meta")
k4.metric("Ticket médio", moeda_energia(ticket))
k5.metric("SS canceladas", f"{qtd_cancelados:,.0f}")
k6.metric("Taxa cancelamento", f"{taxa_cancelamento:.1f}%")

real_grupo = real.groupby("GRUPO", as_index=False)["CNR_ENERGIA"].sum()
comparativo = pd.DataFrame({
    "Grupo": grupos * 2,
    "Tipo": ["Realizado"] * len(grupos) + ["Meta"] * len(grupos),
    "Energia": [float(real_grupo.loc[real_grupo["GRUPO"].eq(g), "CNR_ENERGIA"].sum()) for g in grupos]
               + [metas_grupo.get(g, 0) for g in grupos],
})
c1, c2 = st.columns(2)
with c1:
    fig = px.bar(comparativo, x="Grupo", y="Energia", color="Tipo", barmode="group",
                 title="Meta x realizado de CNR", text="Energia",
                 color_discrete_map={"Realizado": "#38BDF8", "Meta": "#64748B"})
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")
with c2:
    evolucao = df.groupby(["FISCAL_CICLO_STATUS_MES", "STATUS_ROTULO"], as_index=False)["CNR_ENERGIA"].sum()
    evolucao["Mês"] = evolucao["FISCAL_CICLO_STATUS_MES"].map(lambda m: MESES[int(m)].title())
    fig = px.bar(evolucao, x="Mês", y="CNR_ENERGIA", color="STATUS_ROTULO", barmode="group",
                 title="Evolução mensal por status", text="CNR_ENERGIA", color_discrete_map=CORES_STATUS)
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

t1, t2 = st.columns(2)
with t1:
    ticket_grupo = real.groupby("GRUPO").agg(Energia=("CNR_ENERGIA", "sum"), SS=("INSPECAO_ID", "nunique")).reset_index()
    ticket_grupo["Ticket médio"] = ticket_grupo["Energia"].div(ticket_grupo["SS"].replace(0, pd.NA)).fillna(0)
    fig = px.bar(ticket_grupo, x="GRUPO", y="Ticket médio", title="Ticket médio por grupo", text="Ticket médio",
                 color="GRUPO", color_discrete_map={"A": "#38BDF8", "B": "#34D399", "IP": "#F59E0B"})
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False, showlegend=False)
    st.plotly_chart(tema(fig), width="stretch")
with t2:
    ticket_projeto = real.groupby("PROJETO").agg(Energia=("CNR_ENERGIA", "sum"), SS=("INSPECAO_ID", "nunique")).reset_index()
    ticket_projeto["Ticket médio"] = ticket_projeto["Energia"].div(ticket_projeto["SS"].replace(0, pd.NA)).fillna(0)
    ticket_projeto = ticket_projeto.nlargest(10, "Ticket médio").sort_values("Ticket médio")
    fig = px.bar(ticket_projeto, x="Ticket médio", y="PROJETO", orientation="h", title="Ticket médio por projeto",
                 text="Ticket médio", color_discrete_sequence=["#A78BFA"])
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

m1, m2 = st.columns(2)
with m1:
    motivos = cancelados.groupby("MOTIVO", as_index=False).agg(SS=("INSPECAO_ID", "nunique"), Energia=("CNR_ENERGIA", "sum"))
    motivos = motivos.nlargest(10, "SS").sort_values("SS")
    fig = px.bar(motivos, x="SS", y="MOTIVO", orientation="h", title="Maiores motivos de cancelamento",
                 text="SS", color_discrete_sequence=["#F87171"], hover_data=["Energia"])
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")
with m2:
    perfil = df.groupby(["IRREGULARIDADE", "LIGACAO"], as_index=False)["CNR_ENERGIA"].sum()
    fig = px.bar(perfil, x="IRREGULARIDADE", y="CNR_ENERGIA", color="LIGACAO", barmode="group",
                 title="Energia por irregularidade e tipo de ligação", text="CNR_ENERGIA")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

st.markdown("### Base analítica para validação")
colunas = [
    "INSPECAO_ID", "NOVA_REGIONAL", "GRUPO_CNR", "FISCAL_CICLO_STATUS_ANO",
    "FISCAL_CICLO_STATUS_MES", "STATUS_CNR_EQTL", "CNR_ENERGIA",
    "TIPO_IRREGULARIDADE_TOI", "TIPOLIGACAO", "MOTIVO_CANCELAMENTO_DESCRICAO",
    "PROJETO_PERDA", "ARQUIVO_ORIGEM", "ATUALIZADO_EM",
]
colunas = [c for c in colunas if c in df.columns]
validacao = df[colunas].sort_values("CNR_ENERGIA", ascending=False)
st.dataframe(validacao, width="stretch", hide_index=True, height=450)
st.download_button(
    "Baixar base filtrada de CNR",
    validacao.to_csv(index=False, sep=";", encoding="utf-8-sig"),
    file_name="validacao_energia_cnr.csv", mime="text/csv",
)

origem = str(cnr["ARQUIVO_ORIGEM"].dropna().iloc[0]) if "ARQUIVO_ORIGEM" in cnr and not cnr["ARQUIVO_ORIGEM"].dropna().empty else "Base CNR"
atualizado = str(cnr["ATUALIZADO_EM"].dropna().iloc[0]) if "ATUALIZADO_EM" in cnr and not cnr["ATUALIZADO_EM"].dropna().empty else "Não informado"
try:
    atualizado = pd.Timestamp(atualizado).strftime("%d/%m/%Y às %H:%M")
except Exception:
    pass
st.caption(
    f"Dados atualizados em: {atualizado} · Origem: {origem} · "
    "Real CNR considera 1.Faturada e 2.Cancelamento; cancelamento estratégico é demonstrado separadamente."
)
