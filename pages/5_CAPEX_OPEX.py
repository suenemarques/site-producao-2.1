from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="CAPEX e OPEX", page_icon="💰", layout="wide")

BASE = Path(__file__).resolve().parents[1]
ARQ = BASE / "dados" / "capex_opex.parquet"

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def moeda(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tema(fig, altura=420):
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CAD5E2",
        legend_title_text="",
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=1.04, yanchor="bottom",
            entrywidth=0.30, entrywidthmode="fraction",
        ),
        margin=dict(l=25, r=55, t=90, b=45),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)", automargin=True)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", automargin=True)
    return fig


st.markdown(
    """
    <style>
    .stApp{background:#07111F;color:#E8EEF6}
    [data-testid="stSidebar"]{background:#0B1728;border-right:1px solid #1E3047}
    [data-testid="stSidebarNav"]{display:none}
    .block-container{padding-top:1.5rem;max-width:1550px}
    div[data-testid="stMetric"],div[data-testid="stPlotlyChart"]{
        background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:.5rem
    }
    .nav{display:block;padding:.55rem;margin:.25rem 0;border:1px solid #46556A;
        border-radius:.5rem;text-align:center;color:white!important;text-decoration:none!important}
    </style>
    """,
    unsafe_allow_html=True,
)

if not ARQ.is_file():
    st.error("Base CAPEX/OPEX não encontrada.")
    st.info("Execute o Atualizador Único V13.")
    st.stop()


@st.cache_data(ttl=900)
def carregar():
    dados = pd.read_parquet(ARQ)
    dados["DT_CONCLUSAO"] = pd.to_datetime(dados["DT_CONCLUSAO"], errors="coerce")
    return dados


d0 = carregar()

with st.sidebar:
    st.markdown("### 💰 CAPEX e OPEX")
    st.caption("Somente equipes RIOF e MORF")
    st.markdown(
        '<a class="nav" href="/" target="_self">📊 Produção</a>',
        unsafe_allow_html=True,
    )

    for arquivo, rotulo, icone in [
        ("2_Energia_CNR.py", "Energia CNR", "⚡"),
        ("3_Incremento.py", "Incremento", "📈"),
        ("4_MEPE.py", "MEPE", "🎯"),
    ]:
        pagina = f"pages/{arquivo}"
        if (BASE / pagina).is_file():
            st.page_link(pagina, label=rotulo, icon=icone, width="stretch")

    st.button("💰 CAPEX e OPEX", disabled=True, width="stretch")

    pagina_turnos = "pages/6_Validacao_turnos.py"
    if (BASE / pagina_turnos).is_file():
        st.page_link(
            pagina_turnos,
            label="Validação de Turnos",
            icon="🕒",
            width="stretch",
        )

    st.markdown("---")
    regionais_disponiveis = sorted(d0["REGIONAL"].dropna().unique())
    regs = st.multiselect(
        "Regional",
        regionais_disponiveis,
        default=regionais_disponiveis,
        key="capex_regionais",
    )

    meses_disponiveis = sorted(d0["MES_REF"].dropna().unique())
    meses = st.multiselect(
        "Mês",
        meses_disponiveis,
        default=meses_disponiveis,
        format_func=lambda valor: MESES[int(valor)],
        key="capex_meses",
    )

    equipes_disp = sorted(
        d0.loc[d0["REGIONAL"].isin(regs), "EQUIPE"].dropna().unique()
    )
    equipes = st.multiselect(
        "Equipe",
        equipes_disp,
        default=equipes_disp,
        key="capex_equipes",
    )

d = d0[
    d0["REGIONAL"].isin(regs)
    & d0["MES_REF"].isin(meses)
    & d0["EQUIPE"].isin(equipes)
].copy()

totais = d.groupby("CLASSIFICACAO")["VALOR"].sum()
odi = float(totais.get("ODI", 0))
odd = float(totais.get("ODD", 0))
opex = float(totais.get("OPEX", 0))
capex = odi + odd

atualizado = pd.to_datetime(
    d0.get("ATUALIZADO_EM", pd.Series(dtype=str)), errors="coerce"
).max()

st.title("CAPEX e OPEX")
if pd.notna(atualizado):
    st.caption(
        f"Período pela DT_CONCLUSAO · CAPEX = ODI + ODD · "
        f"Dados atualizados em: {atualizado:%d/%m/%Y às %H:%M}"
    )
else:
    st.caption("Período pela DT_CONCLUSAO · CAPEX = ODI + ODD")

c1, c2, c3, c4 = st.columns(4)
c1.metric("CAPEX", moeda(capex))
c2.metric("ODI", moeda(odi))
c3.metric("ODD", moeda(odd))
c4.metric("OPEX", moeda(opex))

base_total = capex + opex
percentual_capex = capex / base_total * 100 if base_total else 0
percentual_opex = opex / base_total * 100 if base_total else 0

p1, p2, p3 = st.columns(3)
p1.metric("% CAPEX", f"{percentual_capex:.1f}%".replace(".", ","))
p2.metric("% OPEX", f"{percentual_opex:.1f}%".replace(".", ","))
p3.metric("Lançamentos", f"{len(d):,}".replace(",", "."))

coluna_a, coluna_b = st.columns(2)
with coluna_a:
    composicao = pd.DataFrame(
        {"Classificação": ["ODI", "ODD", "OPEX"], "Valor": [odi, odd, opex]}
    )
    composicao["Rótulo"] = composicao["Valor"].map(moeda)
    fig = px.bar(
        composicao,
        x="Classificação",
        y="Valor",
        color="Classificação",
        text="Rótulo",
        title="Composição dos custos",
        color_discrete_map={"ODI": "#38BDF8", "ODD": "#A78BFA", "OPEX": "#F59E0B"},
    )
    fig.update_traces(textposition="auto", cliponaxis=False, showlegend=False)
    st.plotly_chart(tema(fig), width="stretch")

with coluna_b:
    mensal = d.groupby(["MES_REF", "CLASSIFICACAO"], as_index=False)["VALOR"].sum()
    mensal["Mês"] = mensal["MES_REF"].map(MESES)
    mensal["Rótulo"] = mensal["VALOR"].map(moeda)
    fig = px.bar(
        mensal,
        x="Mês",
        y="VALOR",
        color="CLASSIFICACAO",
        barmode="stack",
        text="Rótulo",
        title="Evolução mensal",
    )
    fig.update_traces(textposition="auto", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

coluna_a, coluna_b = st.columns(2)
with coluna_a:
    servicos = (
        d.groupby(["TIPO_SERVICO", "CLASSIFICACAO"], as_index=False)
        .agg(Valor=("VALOR", "sum"), Quantidade=("QTD", "sum"))
        .sort_values("Valor")
    )
    fig = px.bar(
        servicos,
        x="Valor",
        y="TIPO_SERVICO",
        orientation="h",
        color="CLASSIFICACAO",
        text="Quantidade",
        title="Serviços que compõem os custos",
    )
    fig.update_traces(textposition="auto", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

with coluna_b:
    equipes_grafico = d.groupby(
        ["EQUIPE", "CLASSIFICACAO"], as_index=False
    )["VALOR"].sum()
    fig = px.bar(
        equipes_grafico,
        x="EQUIPE",
        y="VALOR",
        color="CLASSIFICACAO",
        barmode="stack",
        title="Custos por equipe",
    )
    fig.update_traces(textposition="auto", cliponaxis=False)
    st.plotly_chart(tema(fig), width="stretch")

st.subheader("Base de validação CAPEX/OPEX")
st.dataframe(
    d.sort_values("DT_CONCLUSAO", ascending=False),
    width="stretch",
    hide_index=True,
)
st.download_button(
    "Baixar base de validação",
    d.to_csv(index=False, sep=";").encode("utf-8-sig"),
    "validacao_capex_opex.csv",
    "text/csv",
    width="stretch",
)
