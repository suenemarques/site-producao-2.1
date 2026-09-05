from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Incremento", page_icon="📈", layout="wide")

ANO_ATUAL = 2026
BASE_DIR = Path(__file__).resolve().parents[1]
ARQ_INCREMENTO = BASE_DIR / "dados" / f"incremento_{ANO_ATUAL}.parquet"
ARQ_METAS = BASE_DIR / "METAS 2026.xlsx"
MESES = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}


def normalizar(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def formatar_numero(valor: float, casas: int = 2) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_mwh(valor: float) -> str:
    return f"{formatar_numero(valor)} MWh"


def formatar_inteiro(valor: int | float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


@st.cache_data(ttl=900, show_spinner=False)
def carregar() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = pd.read_parquet(ARQ_INCREMENTO)
    base.columns = [str(c).strip() for c in base.columns]
    base["GANHO_FINAL"] = pd.to_numeric(base["GANHO_FINAL"], errors="coerce").fillna(0)
    base["GANHO_MWH"] = base["GANHO_FINAL"] / 1000
    base["ANO_NORM"] = pd.to_numeric(base["ANO_NORM"], errors="coerce").astype("Int64")
    base["REF_MES"] = pd.to_numeric(base["REF_MES"], errors="coerce").astype("Int64")
    base["REGIONAL_N"] = base["Regional"].map(normalizar)
    base["GRUPO_N"] = base["Grupo"].map(normalizar)
    base["PROJETO_N"] = base["PROJETO"].fillna("Não informado").replace("", "Não informado")
    base["DESC_N"] = base["Desconsiderar"].map(normalizar)
    base["MOTIVO_DESCONSIDERACAO"] = (
        base["Desconsiderar"].fillna("Não informado").replace("", "Não informado")
    )
    base["TIPO_GANHO"] = "Outros"
    base.loc[base["DESC_N"].ne(""), "TIPO_GANHO"] = "Desconsiderado"
    base.loc[base["DESC_N"].eq("") & base["ANO_NORM"].eq(ANO_ATUAL), "TIPO_GANHO"] = "Incremento"
    base.loc[base["DESC_N"].eq("") & base["ANO_NORM"].lt(ANO_ATUAL), "TIPO_GANHO"] = "Residual"
    base["MES_NOME"] = base["REF_MES"].map(lambda m: MESES.get(int(m), "") if pd.notna(m) else "")

    metas = pd.read_excel(ARQ_METAS, sheet_name="METAS 2026")
    metas.columns = [str(c).strip() for c in metas.columns]
    metas.rename(columns={"MÊS": "MES"}, inplace=True)
    for coluna in ["REGIONAL", "MES", "GRUPO", "TIPO DA META"]:
        if coluna not in metas.columns:
            metas[coluna] = ""
        metas[coluna] = metas[coluna].map(normalizar)
    mapa_mes = {normalizar(nome): numero for numero, nome in MESES.items()}
    metas["MES_NUM_META"] = metas["MES"].map(mapa_mes)
    metas.loc[metas["MES_NUM_META"].isna(), "MES_NUM_META"] = pd.to_numeric(
        metas.loc[metas["MES_NUM_META"].isna(), "MES"], errors="coerce"
    )
    metas["QUANTIDADE"] = pd.to_numeric(metas.get("QUANTIDADE", 0), errors="coerce").fillna(0)
    return base, metas


def obter_meta_mensal(
    metas: pd.DataFrame, regionais: list[str], grupos: list[str], meses: list[int]
) -> dict[int, float]:
    regionais_meta = {
        re.sub(r"^\d+\s*[.\-]?\s*", "", normalizar(regional))
        for regional in regionais
    }
    base = metas[
        metas["REGIONAL"].isin(regionais_meta)
        & metas["MES_NUM_META"].isin(meses)
        & metas["TIPO DA META"].str.contains("INCREMENTO", na=False)
    ].copy()
    saida: dict[int, float] = {}
    for mes in meses:
        linhas_mes = base[base["MES_NUM_META"].eq(mes)]
        total = 0.0
        for grupo in grupos:
            tipo_exato = {
                "A": "INCREMENTO AT",
                "B": "INCREMENTO BT",
                "IP": "INCREMENTO IP",
            }.get(grupo, "")
            linhas_grupo = linhas_mes[
                linhas_mes["TIPO DA META"].isin(
                    {tipo_exato, f"META {tipo_exato}"}
                )
            ]
            total += float(linhas_grupo["QUANTIDADE"].sum())
        saida[mes] = total / 1000
    return saida


def tema(fig, altura: int = 400):
    fig.update_layout(
        height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CAD5E2", family="Inter, sans-serif"),
        margin=dict(l=20, r=45, t=90, b=40),
        title=dict(y=.98, x=.02, xanchor="left", yanchor="top"),
        legend=dict(orientation="h", x=.5, xanchor="center", y=1.03, yanchor="bottom", entrywidth=.30, entrywidthmode="fraction"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="#101D2E", font_color="white"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False, automargin=True)
    return fig


st.markdown("""
<style>
.stApp {background:#07111F;color:#E8EEF6}
[data-testid="stSidebar"] {background:#0B1728;border-right:1px solid #1E3047}
[data-testid="stSidebarNav"] {display:none}
.block-container {padding-top:1.5rem;max-width:1550px}
.eyebrow {color:#38BDF8;font-size:.78rem;font-weight:800;letter-spacing:.14em}
.page-title {font-size:2.1rem;font-weight:800;margin:.18rem 0 0}
.subtitle {color:#8FA2B8;margin-bottom:1rem}
.nav-producao {display:block;width:100%;box-sizing:border-box;padding:.55rem .8rem;
margin:.25rem 0;border:1px solid #46556A;border-radius:.5rem;color:#FFF!important;
background:#172235;text-align:center;text-decoration:none!important;font-weight:600}
.nav-producao:hover {border-color:#FFF;background:#223149}
div[data-testid="stPlotlyChart"] {background:#0B1728;border:1px solid #1E3047;border-radius:16px;padding:.25rem .55rem}
div[data-testid="stMetric"] {background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:1rem}
</style>
""", unsafe_allow_html=True)

try:
    base, metas = carregar()
except Exception as erro:
    st.error(f"Não foi possível carregar a base de Incremento: {erro}")
    st.info("Execute o atualizador único para gerar dados/incremento_2026.parquet.")
    st.stop()

with st.sidebar:
    st.markdown("### 📈 Incremento")
    st.caption("Recuperação de Energia · Sul")
    st.markdown('<a class="nav-producao" href="/" target="_self">📊 Produção</a>', unsafe_allow_html=True)
    if (BASE_DIR / "pages" / "2_Energia_CNR.py").is_file():
        st.page_link("pages/2_Energia_CNR.py", label="Energia CNR", icon="⚡", width="stretch")
    st.button("📈 Incremento", disabled=True, width="stretch")
    for pagina, rotulo, icone in [
        ("4_MEPE.py", "MEPE", "🎯"),
        ("5_CAPEX_OPEX.py", "CAPEX e OPEX", "💰"),
        ("6_Validacao_Turnos.py", "Validação de Turnos", "🕒"),
    ]:
        st.page_link(f"pages/{pagina}", label=rotulo, icon=icone, width="stretch")
    st.markdown("---")
    regionais_disp = sorted(base["REGIONAL_N"].dropna().unique())
    regionais = st.multiselect("Regional", regionais_disp, default=regionais_disp)
    grupos_disp = [g for g in ["A", "B", "IP"] if g in set(base["GRUPO_N"])]
    grupos = st.multiselect("Grupo", grupos_disp, default=grupos_disp)
    meses_disp = sorted(base["REF_MES"].dropna().astype(int).unique())
    meses = st.multiselect("Mês do ganho", meses_disp, default=meses_disp, format_func=lambda m: MESES[m].title())
    if st.button("Atualizar leitura das bases", width="stretch"):
        st.cache_data.clear()
        st.rerun()

filtro = (
    base["REGIONAL_N"].isin(regionais) & base["GRUPO_N"].isin(grupos)
    & base["REF_MES"].isin(meses)
)
df = base.loc[filtro].copy()
incremento = df[df["TIPO_GANHO"].eq("Incremento")].copy()
residual = df[df["TIPO_GANHO"].eq("Residual")].copy()
desconsiderado = df[df["TIPO_GANHO"].eq("Desconsiderado")].copy()

st.markdown('<div class="eyebrow">VISÃO ENERGÉTICA</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Incremento</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">{ANO_ATUAL} · {formatar_inteiro(len(df))} registros filtrados · '
    f'{", ".join(regionais) if regionais else "Nenhuma regional"}</div>', unsafe_allow_html=True
)

metas_mes = obter_meta_mensal(metas, regionais, grupos, meses)
meta_total = sum(metas_mes.values())
real_total = float(incremento["GANHO_MWH"].sum())
residual_total = float(residual["GANHO_MWH"].sum())
desconsiderado_total = float(desconsiderado["GANHO_MWH"].sum())
ucs = int(incremento["UC"].nunique())
ticket = real_total / ucs if ucs else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Incremento realizado", formatar_mwh(real_total))
k2.metric("Meta", formatar_mwh(meta_total))
k3.metric("Atingimento", f"{formatar_numero(real_total / meta_total * 100, 1)}%" if meta_total else "Sem meta")
k4.metric("Ticket médio por UC", formatar_mwh(ticket))
k5, k6, k7 = st.columns(3)
k5.metric("Residual", formatar_mwh(residual_total))
k6.metric("Desconsiderado", formatar_mwh(desconsiderado_total))
k7.metric("UCs com incremento", formatar_inteiro(ucs))

mensal_real = incremento.groupby("REF_MES")["GANHO_MWH"].sum()
comparativo = pd.DataFrame({
    "Mês número": meses * 2,
    "Tipo": ["Meta"] * len(meses) + ["Realizado"] * len(meses),
    "Energia (MWh)": [metas_mes.get(m, 0) for m in meses]
    + [float(mensal_real.get(m, 0)) for m in meses],
})
comparativo["Mês"] = comparativo["Mês número"].map(lambda m: MESES[m].title())
comparativo["Rótulo"] = comparativo["Energia (MWh)"].map(formatar_mwh)

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(
        comparativo, x="Mês", y="Energia (MWh)", color="Tipo", barmode="group",
        title="Meta x realizado de Incremento", text="Rótulo",
        category_orders={"Tipo": ["Meta", "Realizado"]},
        color_discrete_map={"Meta": "#64748B", "Realizado": "#38BDF8"},
    )
    fig.update_traces(textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema(fig), width="stretch")
with c2:
    evolucao = pd.DataFrame({"Mês número": meses})
    evolucao["Ganho (MWh)"] = evolucao["Mês número"].map(mensal_real).fillna(0)
    evolucao["Mês"] = evolucao["Mês número"].map(lambda m: MESES[m].title())
    evolucao["Anterior"] = evolucao["Ganho (MWh)"].shift(1)
    evolucao["Situação"] = "Primeiro mês"
    evolucao.loc[evolucao["Ganho (MWh)"].ge(evolucao["Anterior"]), "Situação"] = "Crescimento"
    evolucao.loc[evolucao["Ganho (MWh)"].lt(evolucao["Anterior"]), "Situação"] = "Queda"
    evolucao["Rótulo"] = evolucao["Ganho (MWh)"].map(formatar_mwh)
    fig = px.bar(
        evolucao, x="Mês", y="Ganho (MWh)", color="Situação",
        title="Ganho mensal", text="Rótulo",
        color_discrete_map={"Crescimento": "#34D399", "Queda": "#F87171", "Primeiro mês": "#38BDF8"},
    )
    fig.update_traces(textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema(fig), width="stretch")

t1, t2 = st.columns(2)
with t1:
    ticket_projeto = incremento.groupby("PROJETO_N").agg(
        Energia=("GANHO_MWH", "sum"), UCs=("UC", "nunique")
    ).reset_index()
    ticket_projeto["Ticket médio (MWh)"] = ticket_projeto["Energia"].div(ticket_projeto["UCs"].replace(0, pd.NA)).fillna(0)
    ticket_projeto = ticket_projeto.sort_values("Ticket médio (MWh)")
    ticket_projeto["Rótulo"] = ticket_projeto["Ticket médio (MWh)"].map(formatar_mwh)
    fig = px.bar(ticket_projeto, x="Ticket médio (MWh)", y="PROJETO_N", orientation="h",
                 title="Ticket médio por projeto", text="Rótulo", color_discrete_sequence=["#A78BFA"])
    fig.update_traces(textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema(fig), width="stretch")
with t2:
    grupo = incremento.groupby("GRUPO_N", as_index=False)["GANHO_MWH"].sum()
    grupo["Rótulo"] = grupo["GANHO_MWH"].map(formatar_mwh)
    fig = px.bar(grupo, x="GRUPO_N", y="GANHO_MWH", color="GRUPO_N", text="Rótulo",
                 title="Incremento por grupo", color_discrete_map={"A": "#38BDF8", "B": "#34D399", "IP": "#F59E0B"})
    fig.update_traces(textposition="auto", cliponaxis=False, insidetextanchor="middle", showlegend=False)
    st.plotly_chart(tema(fig), width="stretch")

d1, d2 = st.columns(2)
with d1:
    motivos = desconsiderado.groupby("MOTIVO_DESCONSIDERACAO", as_index=False).agg(
        Registros=("UC", "size"), Energia_MWh=("GANHO_MWH", "sum")
    ).sort_values("Registros")
    fig = px.bar(motivos, x="Registros", y="MOTIVO_DESCONSIDERACAO", orientation="h",
                 title="Incrementos desconsiderados e motivos", text="Registros",
                 color_discrete_sequence=["#F87171"], hover_data={"Energia_MWh": ":.2f"})
    fig.update_traces(textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema(fig), width="stretch")
with d2:
    residual_graf = residual.groupby(["ANO_NORM", "PROJETO_N"], as_index=False)["GANHO_MWH"].sum()
    fig = px.bar(residual_graf, x="ANO_NORM", y="GANHO_MWH", color="PROJETO_N", barmode="stack",
                 title="Residual por ano da normalização e projeto")
    st.plotly_chart(tema(fig), width="stretch")

st.markdown("### Ganho mensal por unidade consumidora")
pivot_uc = incremento.pivot_table(index="UC", columns="REF_MES", values="GANHO_MWH", aggfunc="sum", fill_value=0)
pivot_uc = pivot_uc.reindex(columns=meses, fill_value=0)
pivot_uc.columns = [MESES[m].title() for m in pivot_uc.columns]

def destacar_queda(linha: pd.Series) -> list[str]:
    estilos = [""] * len(linha)
    for indice in range(1, len(linha)):
        if linha.iloc[indice] < linha.iloc[indice - 1]:
            estilos[indice] = "background-color:#7F1D1D;color:#FFFFFF;font-weight:700"
    return estilos

st.dataframe(
    pivot_uc.style.apply(destacar_queda, axis=1).format(
        lambda valor: formatar_numero(valor)
    ),
    width="stretch", height=420,
)
st.caption("Células vermelhas indicam ganho inferior ao mês anterior da mesma UC.")

st.markdown("### Base analítica para validação")
colunas = [
    "UC", "Regional", "Grupo", "Data_Norm", "ANO_NORM", "REF_GANHO", "REF_MES",
    "PROJETO", "TIPO_GANHO", "Desconsiderar", "GANHO_MWH",
    "ARQUIVO_ORIGEM", "ATUALIZADO_EM",
]
colunas = [c for c in colunas if c in df.columns]
validacao = df[colunas].sort_values("GANHO_MWH", ascending=False)
st.dataframe(validacao, width="stretch", hide_index=True, height=470)
st.download_button(
    "Baixar base filtrada de Incremento",
    validacao.to_csv(index=False, sep=";", encoding="utf-8-sig"),
    file_name="validacao_incremento.csv", mime="text/csv",
)

origem = str(base["ARQUIVO_ORIGEM"].dropna().iloc[0]) if "ARQUIVO_ORIGEM" in base and not base["ARQUIVO_ORIGEM"].dropna().empty else "Base Incremento"
atualizado = str(base["ATUALIZADO_EM"].dropna().iloc[0]) if "ATUALIZADO_EM" in base and not base["ATUALIZADO_EM"].dropna().empty else "Não informado"
try:
    atualizado = pd.Timestamp(atualizado).strftime("%d/%m/%Y às %H:%M")
except Exception:
    pass
st.caption(
    f"Dados atualizados em: {atualizado} · Origem: {origem} · "
    "Incremento considera Data_Norm no ano atual e Desconsiderar vazio; anos anteriores são residuais."
)
