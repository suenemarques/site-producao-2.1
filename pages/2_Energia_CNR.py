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


def resumir_motivo(valor: object) -> str:
    motivo = normalizar(valor)
    if motivo.startswith("PROC:") or motivo.startswith("PROC ") or "JURID" in motivo:
        return "Processo Jurídico"
    if "ESTRATEG" in motivo:
        return "Cancelamento estratégico"
    if "REFATUR" in motivo:
        return "Refaturamento"
    if "CANCELAMENTO CNR" in motivo or motivo == "CANCELAMENTO":
        return "Cancelamento CNR"
    return str(valor).strip() if str(valor).strip() else "Não informado"


def resumir_ligacao(valor: object) -> str:
    ligacao = normalizar(valor)
    if "MONOFAS" in ligacao:
        return "Monofásico"
    if "BIFAS" in ligacao:
        return "Bifásico"
    if "TRIFAS" in ligacao:
        return "Trifásico"
    return str(valor).strip().title() if str(valor).strip() else "Não informado"


def formatar_mwh(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " MWh"


def formatar_inteiro(valor: float | int) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def formatar_percentual(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",") + "%"


def pontos_selecionados(evento) -> list[dict]:
    try:
        return list(evento.selection.points)
    except (AttributeError, TypeError):
        try:
            return list(evento.get("selection", {}).get("points", []))
        except (AttributeError, TypeError):
            return []


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
    cnr["LIGACAO"] = (
        cnr["TIPOLIGACAO"].fillna("Não informado").replace("", "Não informado")
        .map(resumir_ligacao)
    )
    cnr["MOTIVO"] = cnr["MOTIVO_CANCELAMENTO_DESCRICAO"].fillna("Não informado").replace("", "Não informado")
    cnr["MOTIVO_RESUMIDO"] = cnr["MOTIVO"].map(resumir_motivo)
    cnr["MES_NOME"] = cnr["FISCAL_CICLO_STATUS_MES"].map(MESES)

    metas = pd.read_excel(ARQ_METAS, sheet_name="METAS 2026")
    metas.columns = [str(c).strip() for c in metas.columns]
    metas.rename(columns={"MÊS": "MES"}, inplace=True)
    for coluna in ["REGIONAL", "MES", "GRUPO", "TIPO DA META"]:
        if coluna not in metas.columns:
            metas[coluna] = ""
        metas[coluna] = metas[coluna].map(normalizar)
    nomes_para_numero = {normalizar(nome): numero for numero, nome in MESES.items()}
    metas["MES_NUM_META"] = metas["MES"].map(nomes_para_numero)
    metas.loc[metas["MES_NUM_META"].isna(), "MES_NUM_META"] = pd.to_numeric(
        metas.loc[metas["MES_NUM_META"].isna(), "MES"], errors="coerce"
    )
    metas["QUANTIDADE"] = pd.to_numeric(metas.get("QUANTIDADE", 0), errors="coerce").fillna(0)
    return cnr, metas


def meta_cnr(metas: pd.DataFrame, regionais: list[str], grupos: list[str], meses: list[int]) -> dict[str, float]:
    regionais_meta = {
        re.sub(r"^\d+\s*[.\-]?\s*", "", normalizar(regional))
        for regional in regionais
    }
    base = metas[
        metas["REGIONAL"].isin(regionais_meta)
        & metas["MES_NUM_META"].isin(meses)
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
        # A planilha de metas armazena energia em kWh; o painel exibe MWh.
        resultado[grupo] = float(linhas["QUANTIDADE"].sum()) / 1000
    return resultado


def tema(fig, altura: int = 390):
    fig.update_layout(
        height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CAD5E2", family="Inter, sans-serif"),
        margin=dict(l=15, r=20, t=90, b=35),
        title=dict(y=.98, x=.02, xanchor="left", yanchor="top"),
        legend=dict(orientation="h", y=1.03, x=0, yanchor="bottom"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="#101D2E", font_color="white"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    return fig


def energia_mwh(valor: float) -> str:
    return formatar_mwh(valor)


st.markdown("""
<style>
.stApp {background:#07111F;color:#E8EEF6}
[data-testid="stSidebar"] {background:#0B1728;border-right:1px solid #1E3047}
[data-testid="stSidebarNav"] {display:none}
.block-container {padding-top:1.5rem;max-width:1550px}
.eyebrow {color:#38BDF8;font-size:.78rem;font-weight:800;letter-spacing:.14em}
.page-title {font-size:2.1rem;font-weight:800;margin:.18rem 0 0}
.subtitle {color:#8FA2B8;margin-bottom:1rem}
.nav-producao {
  display:block; width:100%; box-sizing:border-box; padding:.55rem .8rem;
  margin:.25rem 0; border:1px solid #46556A; border-radius:.5rem;
  color:#FFFFFF !important; background:#172235; text-align:center;
  text-decoration:none !important; font-weight:600;
}
.nav-producao:hover {border-color:#FFFFFF;background:#223149}
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
    st.markdown(
        '<a class="nav-producao" href="/" target="_self">📊 Produção</a>',
        unsafe_allow_html=True,
    )
    st.button("⚡ Energia CNR", disabled=True, width="stretch")
    st.page_link(
        "pages/3_Incremento.py", label="Incremento", icon="📈",
        width="stretch",
    )
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
    if st.button("Limpar seleções dos gráficos", width="stretch"):
        for chave in [
            "cnr_meta", "cnr_evolucao", "cnr_ticket_grupo",
            "cnr_ticket_projeto", "cnr_motivos", "cnr_perfil",
        ]:
            st.session_state.pop(chave, None)
        st.rerun()

filtro = (
    cnr["REGIONAL"].isin(regionais) & cnr["GRUPO"].isin(grupos)
    & cnr["FISCAL_CICLO_STATUS_MES"].isin(meses) & cnr["STATUS_ROTULO"].isin(status)
    & cnr["PROJETO"].isin(projetos) & cnr["IRREGULARIDADE"].isin(irregularidades)
    & cnr["LIGACAO"].isin(ligacoes)
)
df = cnr.loc[filtro].copy()
faturados = df[df["STATUS_ROTULO"].eq("Faturada")].copy()
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
        f"⚠️ Alerta de cancelamento: "
        f"{formatar_inteiro(recentes['INSPECAO_ID'].nunique())} SS e "
        f"{formatar_mwh(recentes['CNR_ENERGIA'].abs().sum() / 1000)} cancelados em "
        f"{MESES[ultimo_mes_cancelado].title()}."
    )
    with st.expander("Ver cancelamentos do alerta"):
        recentes = recentes.copy()
        recentes["CNR_ENERGIA_MWH"] = recentes["CNR_ENERGIA"].abs() / 1000
        st.dataframe(
            recentes[["INSPECAO_ID", "NOVA_REGIONAL", "GRUPO_CNR", "STATUS_CNR_EQTL",
                      "CNR_ENERGIA_MWH", "MOTIVO_CANCELAMENTO_DESCRICAO", "PROJETO_PERDA"]]
            .sort_values("CNR_ENERGIA_MWH", ascending=False),
            width="stretch", hide_index=True,
        )

metas_grupo = meta_cnr(metas, regionais, grupos, meses)
meta_total = sum(metas_grupo.values())
energia_faturada_mwh = float(faturados["CNR_ENERGIA"].sum()) / 1000
energia_cancelada_mwh = float(cancelados["CNR_ENERGIA"].abs().sum()) / 1000
energia_real_mwh = energia_faturada_mwh - energia_cancelada_mwh
qtd_processos = int(df["INSPECAO_ID"].nunique())
qtd_calculadas = qtd_processos
qtd_cancelados = int(cancelados["INSPECAO_ID"].nunique())
ticket_mwh = energia_real_mwh / qtd_calculadas if qtd_calculadas else 0
taxa_cancelamento = qtd_cancelados / qtd_processos * 100 if qtd_processos else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Real CNR", energia_mwh(energia_real_mwh), help="Faturado menos cancelado")
k2.metric("Meta CNR", energia_mwh(meta_total))
k3.metric("Atingimento", formatar_percentual(energia_real_mwh / meta_total * 100) if meta_total else "Sem meta")
k4.metric("Ticket médio", energia_mwh(ticket_mwh))
k5, k6, k7 = st.columns(3)
k5.metric("SS calculadas", formatar_inteiro(qtd_calculadas))
k6.metric("SS canceladas", formatar_inteiro(qtd_cancelados))
k7.metric("Taxa cancelamento", formatar_percentual(taxa_cancelamento))

if meta_total == 0:
    st.info(
        "Nenhuma meta de CNR foi localizada para a combinação de regional, grupo e mês "
        "selecionada. Confira se a coluna TIPO DA META contém 'CNR'."
    )

st.caption(
    "Clique em uma barra dos gráficos para filtrar a base analítica. "
    "Para desfazer, clique em uma área vazia do gráfico ou use Limpar seleções."
)

faturado_grupo = faturados.groupby("GRUPO")["CNR_ENERGIA"].sum()
cancelado_grupo = cancelados.groupby("GRUPO")["CNR_ENERGIA"].apply(lambda s: s.abs().sum())
comparativo = pd.DataFrame({
    "Grupo": grupos * 2,
    "Tipo": ["Meta"] * len(grupos) + ["Realizado"] * len(grupos),
    "Energia (MWh)": [metas_grupo.get(g, 0) for g in grupos] + [
        (float(faturado_grupo.get(g, 0)) - float(cancelado_grupo.get(g, 0))) / 1000
        for g in grupos
    ],
})
comparativo["Rótulo"] = comparativo["Energia (MWh)"].map(formatar_mwh)
c1, c2 = st.columns(2)
with c1:
    fig = px.bar(comparativo, x="Grupo", y="Energia (MWh)", color="Tipo", barmode="group",
                 title="Meta x realizado de CNR", text="Rótulo",
                 category_orders={"Tipo": ["Meta", "Realizado"]},
                 color_discrete_map={"Realizado": "#38BDF8", "Meta": "#64748B"})
    fig.update_traces(textposition="outside", cliponaxis=False)
    selecao_meta = st.plotly_chart(
        tema(fig), width="stretch", key="cnr_meta", on_select="rerun", selection_mode="points"
    )
with c2:
    evolucao = df.groupby(["FISCAL_CICLO_STATUS_MES", "STATUS_ROTULO"], as_index=False)["CNR_ENERGIA"].sum()
    evolucao["Energia (MWh)"] = evolucao["CNR_ENERGIA"].abs() / 1000
    evolucao["Rótulo"] = evolucao["Energia (MWh)"].map(formatar_mwh)
    evolucao["Mês"] = evolucao["FISCAL_CICLO_STATUS_MES"].map(lambda m: MESES[int(m)].title())
    fig = px.bar(evolucao, x="Mês", y="Energia (MWh)", color="STATUS_ROTULO", barmode="group",
                 title="Evolução mensal por status", text="Rótulo", color_discrete_map=CORES_STATUS)
    fig.update_traces(textposition="outside", cliponaxis=False)
    selecao_evolucao = st.plotly_chart(
        tema(fig), width="stretch", key="cnr_evolucao", on_select="rerun", selection_mode="points"
    )

t1, t2 = st.columns(2)
with t1:
    ticket_grupo = df.groupby("GRUPO").agg(SS=("INSPECAO_ID", "nunique")).reset_index()
    ticket_grupo["Real (MWh)"] = ticket_grupo["GRUPO"].map(
        lambda g: (float(faturado_grupo.get(g, 0)) - float(cancelado_grupo.get(g, 0))) / 1000
    )
    ticket_grupo["Ticket médio (MWh)"] = ticket_grupo["Real (MWh)"].div(ticket_grupo["SS"].replace(0, pd.NA)).fillna(0)
    ticket_grupo["Rótulo"] = ticket_grupo["Ticket médio (MWh)"].map(formatar_mwh)
    fig = px.bar(ticket_grupo, x="GRUPO", y="Ticket médio (MWh)", title="Ticket médio por grupo", text="Rótulo",
                 color="GRUPO", color_discrete_map={"A": "#38BDF8", "B": "#34D399", "IP": "#F59E0B"})
    fig.update_traces(textposition="outside", cliponaxis=False, showlegend=False)
    selecao_ticket_grupo = st.plotly_chart(
        tema(fig), width="stretch", key="cnr_ticket_grupo", on_select="rerun", selection_mode="points"
    )
with t2:
    projeto_status = df.pivot_table(index="PROJETO", columns="STATUS_ROTULO", values="CNR_ENERGIA", aggfunc="sum", fill_value=0)
    zero_projeto = pd.Series(0.0, index=projeto_status.index)
    energia_faturada_projeto = projeto_status["Faturada"] if "Faturada" in projeto_status else zero_projeto
    energia_cancelada_projeto = projeto_status["Cancelamento"] if "Cancelamento" in projeto_status else zero_projeto
    energia_estrategica_projeto = projeto_status["Cancelamento Estratégico"] if "Cancelamento Estratégico" in projeto_status else zero_projeto
    projeto_status["Real (MWh)"] = (
        energia_faturada_projeto - energia_cancelada_projeto.abs()
        - energia_estrategica_projeto.abs()
    ) / 1000
    ss_projeto = df.groupby("PROJETO")["INSPECAO_ID"].nunique()
    ticket_projeto = projeto_status[["Real (MWh)"]].join(ss_projeto.rename("SS")).reset_index()
    ticket_projeto["Ticket médio (MWh)"] = ticket_projeto["Real (MWh)"].div(ticket_projeto["SS"].replace(0, pd.NA)).fillna(0)
    ticket_projeto = ticket_projeto.nlargest(10, "Ticket médio (MWh)").sort_values("Ticket médio (MWh)")
    ticket_projeto["Rótulo"] = ticket_projeto["Ticket médio (MWh)"].map(formatar_mwh)
    fig = px.bar(ticket_projeto, x="Ticket médio (MWh)", y="PROJETO", orientation="h", title="Ticket médio por projeto",
                 text="Rótulo", color_discrete_sequence=["#A78BFA"])
    fig.update_traces(textposition="outside", cliponaxis=False)
    selecao_ticket_projeto = st.plotly_chart(
        tema(fig), width="stretch", key="cnr_ticket_projeto", on_select="rerun", selection_mode="points"
    )

m1, m2 = st.columns(2)
with m1:
    motivos = cancelados.groupby("MOTIVO_RESUMIDO", as_index=False).agg(SS=("INSPECAO_ID", "nunique"), Energia_kWh=("CNR_ENERGIA", "sum"))
    motivos["Energia (MWh)"] = motivos["Energia_kWh"].abs() / 1000
    motivos = motivos.nlargest(10, "SS").sort_values("SS")
    fig = px.bar(motivos, x="SS", y="MOTIVO_RESUMIDO", orientation="h", title="Maiores motivos de cancelamento",
                 text="SS", color_discrete_sequence=["#F87171"], hover_data={"Energia (MWh)": ":.2f", "Energia_kWh": False})
    fig.update_traces(textposition="outside", cliponaxis=False)
    selecao_motivos = st.plotly_chart(
        tema(fig), width="stretch", key="cnr_motivos", on_select="rerun", selection_mode="points"
    )
with m2:
    perfil = df.groupby(["IRREGULARIDADE", "LIGACAO"], as_index=False)["CNR_ENERGIA"].sum()
    perfil["Energia (MWh)"] = perfil["CNR_ENERGIA"].abs() / 1000
    perfil["Rótulo"] = perfil["Energia (MWh)"].map(formatar_mwh)
    fig = px.bar(perfil, x="IRREGULARIDADE", y="Energia (MWh)", color="LIGACAO", barmode="group",
                 title="Energia por irregularidade e tipo de ligação", text="Rótulo",
                 category_orders={"LIGACAO": ["Monofásico", "Bifásico", "Trifásico"]})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig = tema(fig)
    fig.update_layout(legend=dict(
        title_text="", orientation="h", x=.5, xanchor="center",
        y=1.03, yanchor="bottom",
    ))
    selecao_perfil = st.plotly_chart(
        fig, width="stretch", key="cnr_perfil", on_select="rerun", selection_mode="points"
    )

st.markdown("### Base analítica para validação")
validacao_df = df.copy()
for evento in [selecao_meta, selecao_ticket_grupo]:
    valores = {str(p.get("x")) for p in pontos_selecionados(evento)}
    if valores:
        validacao_df = validacao_df[validacao_df["GRUPO"].isin(valores)]
valores = {str(p.get("x")) for p in pontos_selecionados(selecao_evolucao)}
if valores:
    meses_escolhidos = [numero for numero, nome in MESES.items() if nome.title() in valores]
    validacao_df = validacao_df[validacao_df["FISCAL_CICLO_STATUS_MES"].isin(meses_escolhidos)]
valores = {str(p.get("y")) for p in pontos_selecionados(selecao_ticket_projeto)}
if valores:
    validacao_df = validacao_df[validacao_df["PROJETO"].isin(valores)]
valores = {str(p.get("y")) for p in pontos_selecionados(selecao_motivos)}
if valores:
    validacao_df = validacao_df[validacao_df["MOTIVO_RESUMIDO"].isin(valores)]
valores = {str(p.get("x")) for p in pontos_selecionados(selecao_perfil)}
if valores:
    validacao_df = validacao_df[validacao_df["IRREGULARIDADE"].isin(valores)]

validacao_df["CNR_ENERGIA_MWH"] = validacao_df["CNR_ENERGIA"] / 1000
colunas = [
    "INSPECAO_ID", "NOVA_REGIONAL", "GRUPO_CNR", "FISCAL_CICLO_STATUS_ANO",
    "FISCAL_CICLO_STATUS_MES", "STATUS_CNR_EQTL", "CNR_ENERGIA_MWH",
    "TIPO_IRREGULARIDADE_TOI", "TIPOLIGACAO", "MOTIVO_CANCELAMENTO_DESCRICAO",
    "PROJETO_PERDA", "ARQUIVO_ORIGEM", "ATUALIZADO_EM",
]
colunas = [c for c in colunas if c in validacao_df.columns]
validacao = validacao_df[colunas].sort_values("CNR_ENERGIA_MWH", ascending=False)
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
    "Real CNR = energia faturada menos cancelamentos, incluindo cancelamento estratégico."
)
