from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from tema_neon import aplicar_tema_neon

st.set_page_config(page_title="MEPE", page_icon="🎯", layout="wide")
aplicar_tema_neon()
BASE = Path(__file__).resolve().parents[1]
ARQ = BASE / "dados" / "mepe.parquet"
MESES = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

def numero(v, casas=2): return f"{v:,.{casas}f}".replace(",","X").replace(".",",").replace("X",".")
def localizar_coluna(dados, *nomes):
    mapa = {str(c).strip().upper(): c for c in dados.columns}
    return next((mapa[n.upper()] for n in nomes if n.upper() in mapa), None)

def soma_equipe(dados, coluna):
    if coluna is None:
        return pd.Series(pd.NA, index=sorted(dados.PRX_DESCRICAO.unique()), dtype="Float64")
    valores = pd.to_numeric(dados[coluna], errors="coerce")
    return valores.groupby(dados.PRX_DESCRICAO).sum(min_count=1)

def media_equipe(dados, coluna):
    valores = pd.to_numeric(dados[coluna], errors="coerce")
    return valores.groupby(dados.PRX_DESCRICAO).mean()

def classificar_mepe(pontos):
    if pd.isna(pontos): return "Não informada"
    if pontos >= 80: return "A"
    if pontos >= 60: return "B"
    if pontos >= 40: return "C"
    return "D"

def cor_classificacao(valor):
    cores = {
        "A": "background-color:#14532D;color:#DCFCE7;font-weight:800",
        "B": "background-color:#713F12;color:#FEF9C3;font-weight:800",
        "C": "background-color:#7C2D12;color:#FFEDD5;font-weight:800",
        "D": "background-color:#7F1D1D;color:#FEE2E2;font-weight:800",
    }
    classe = str(valor).strip().upper().replace("CLASSE ", "")
    return cores.get(classe, "")

def tema(fig, h=420):
    fig.update_layout(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#CAD5E2",legend_title_text="",legend=dict(orientation="h",x=.5,xanchor="center",y=1.04,yanchor="bottom"),margin=dict(l=25,r=50,t=90,b=45))
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)",automargin=True)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)",automargin=True)
    return fig

st.markdown("""<style>.stApp{background:#07111F;color:#E8EEF6}[data-testid="stSidebar"]{background:#0B1728;border-right:1px solid #1E3047}[data-testid="stSidebarNav"]{display:none}.block-container{padding-top:1.5rem;max-width:1550px}div[data-testid="stMetric"],div[data-testid="stPlotlyChart"]{background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:.5rem}.nav{display:block;padding:.55rem;margin:.25rem 0;border:1px solid #46556A;border-radius:.5rem;text-align:center;color:white!important;text-decoration:none!important}</style>""",unsafe_allow_html=True)
if not ARQ.is_file():
    st.error("Base MEPE não encontrada."); st.info("Execute o Atualizador Único V13 para gerar dados/mepe.parquet."); st.stop()

@st.cache_data(ttl=900)
def carregar(): return pd.read_parquet(ARQ)
df0 = carregar()
with st.sidebar:
    st.markdown("### 🎯 MEPE"); st.caption("Recuperação de Energia · Sul")
    st.markdown('<a class="nav" href="/" target="_self">📊 Produção</a>',unsafe_allow_html=True)
    for arq,label,icone in [("2_Energia_CNR.py","Energia CNR","⚡"),("3_Incremento.py","Incremento","📈")]:
        if (BASE/"pages"/arq).is_file(): st.page_link(f"pages/{arq}",label=label,icon=icone,width="stretch")
    st.button("🎯 MEPE",disabled=True,width="stretch")
    for arq,label,icone in [("5_CAPEX_OPEX.py","CAPEX e OPEX","💰"),("6_Validacao_Turnos.py","Validação de Turnos","🕒")]:
        if (BASE/"pages"/arq).is_file(): st.page_link(f"pages/{arq}",label=label,icon=icone,width="stretch")
    st.markdown("---")
    regs=st.multiselect("Regional",sorted(df0.REGIONAL_MEPE.unique()),default=sorted(df0.REGIONAL_MEPE.unique()))
    meses=st.multiselect("Mês",sorted(df0.MES_REF.unique()),default=sorted(df0.MES_REF.unique()),format_func=lambda x:MESES[int(x)])
    equipes=st.multiselect("Equipe",sorted(df0.PRX_DESCRICAO.unique()),default=sorted(df0.PRX_DESCRICAO.unique()))
df=df0[df0.REGIONAL_MEPE.isin(regs)&df0.MES_REF.isin(meses)&df0.PRX_DESCRICAO.isin(equipes)].copy()
atualizado=pd.to_datetime(df0.get("ATUALIZADO_EM",pd.Series(dtype=str)),errors="coerce").max()
st.title("MEPE"); st.caption(f"{len(df):,.0f} combinações de equipe e mês filtradas · Dados atualizados em: {atualizado:%d/%m/%Y às %H:%M}" if pd.notna(atualizado) else f"{len(df):,.0f} combinações filtradas".replace(",","."))
ups,cnr,inc,total=[float(df[c].sum()) for c in ["PONT_UPS","PONT_CNR","PONT_INC","PONT_TOTAL"]]
c1,c2,c3,c4=st.columns(4); c1.metric("Pontuação UPS",numero(ups)); c2.metric("Pontuação CNR",numero(cnr)); c3.metric("Pontuação Incremento",numero(inc)); c4.metric("Pontuação total",numero(total))

# Quadro gerencial consolidado por equipe. Os aliases permitem compatibilidade
# com diferentes versões do atualizador sem alterar a regra gravada no parquet.
col_meta_ups = localizar_coluna(df, "META_UPS_PONT", "META_UPS", "META_UPS_EQUIPE", "META_FISCALIZACAO", "META_PRODUCAO")
col_real_ups = localizar_coluna(df, "REAL_UPS_PONT", "REAL_UPS", "UPS_REALIZADO", "QTD_UPS", "REAL_FISCALIZACAO")
col_meta_cnr = localizar_coluna(df, "META_CNR_KWH", "META_CNR", "META_CNR_EQUIPE")
col_real_cnr = localizar_coluna(df, "REAL_CNR_KWH", "REAL_CNR", "CNR_REALIZADO")
col_meta_inc = localizar_coluna(df, "META_INC_KWH", "META_INCREMENTO_KWH", "META_INC", "META_INCREMENTO")
col_real_inc = localizar_coluna(df, "REAL_INC_KWH", "REAL_INCREMENTO_KWH", "REAL_INC", "INCREMENTO_REALIZADO")
col_classe = localizar_coluna(df, "CLASSIFICACAO", "CLASSIFICACAO_MEPE", "CLASSE", "CLASSE_MEPE")

indice_equipes = sorted(df.PRX_DESCRICAO.dropna().unique())
quadro = pd.DataFrame(index=indice_equipes)
quadro.index.name = "Equipe"
quadro["Meta UPS"] = soma_equipe(df, col_meta_ups).reindex(indice_equipes)
quadro["Realizado UPS"] = soma_equipe(df, col_real_ups).reindex(indice_equipes)
quadro["Pontuação UPS"] = media_equipe(df, "PONT_UPS").reindex(indice_equipes)
quadro["Meta CNR (kWh)"] = soma_equipe(df, col_meta_cnr).reindex(indice_equipes)
quadro["Realizado CNR (kWh)"] = soma_equipe(df, col_real_cnr).reindex(indice_equipes)
quadro["Pontuação CNR"] = media_equipe(df, "PONT_CNR").reindex(indice_equipes)
quadro["Meta INC (kWh)"] = soma_equipe(df, col_meta_inc).reindex(indice_equipes)
quadro["Realizado INC (kWh)"] = soma_equipe(df, col_real_inc).reindex(indice_equipes)
quadro["Pontuação INC"] = media_equipe(df, "PONT_INC").reindex(indice_equipes)
quadro["Pontuação Total"] = media_equipe(df, "PONT_TOTAL").reindex(indice_equipes)
if col_classe:
    classes = (
        df.sort_values("MES_REF")
        .dropna(subset=[col_classe])
        .groupby("PRX_DESCRICAO")[col_classe]
        .last()
    )
    quadro["Classificação"] = classes.reindex(indice_equipes).fillna("Não informada")
else:
    quadro["Classificação"] = quadro["Pontuação Total"].map(classificar_mepe)
quadro = quadro.reset_index()

st.subheader("Meta x realizado e classificação por equipe")
st.caption("Metas e realizados somados nos meses selecionados; pontuações pela média mensal. Classificação: A ≥ 80, B ≥ 60, C ≥ 40 e D < 40 pontos.")
formatos = {
    "Meta UPS": "{:,.2f}", "Realizado UPS": "{:,.2f}", "Pontuação UPS": "{:,.2f}",
    "Meta CNR (kWh)": "{:,.2f}", "Realizado CNR (kWh)": "{:,.2f}", "Pontuação CNR": "{:,.2f}",
    "Meta INC (kWh)": "{:,.2f}", "Realizado INC (kWh)": "{:,.2f}", "Pontuação INC": "{:,.2f}",
    "Pontuação Total": "{:,.2f}",
}
st.dataframe(
    quadro.style.format(formatos, na_rep="—").applymap(cor_classificacao, subset=["Classificação"]),
    width="stretch", hide_index=True, height=min(520, 85 + len(quadro) * 35),
)

long=df.melt(id_vars=["PRX_DESCRICAO","MES_REF"],value_vars=["PONT_UPS","PONT_CNR","PONT_INC"],var_name="Indicador",value_name="Pontos")
long["Indicador"]=long["Indicador"].map({"PONT_UPS":"UPS","PONT_CNR":"CNR","PONT_INC":"Incremento"})
equipe=long.groupby(["PRX_DESCRICAO","Indicador"],as_index=False).Pontos.sum()
fig=px.bar(equipe,x="PRX_DESCRICAO",y="Pontos",color="Indicador",barmode="stack",text_auto=".1f",title="Pontuação MEPE por equipe",color_discrete_map={"UPS":"#38BDF8","CNR":"#F59E0B","Incremento":"#34D399"})
fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig,500),width="stretch")

a,b=st.columns(2)
with a:
    mensal=df.groupby("MES_REF",as_index=False)[["PONT_UPS","PONT_CNR","PONT_INC"]].sum().melt("MES_REF",var_name="Indicador",value_name="Pontos")
    mensal["Mês"]=mensal.MES_REF.map(MESES); mensal["Indicador"]=mensal.Indicador.map({"PONT_UPS":"UPS","PONT_CNR":"CNR","PONT_INC":"Incremento"})
    fig=px.line(mensal,x="Mês",y="Pontos",color="Indicador",markers=True,text="Pontos",title="Evolução mensal da pontuação")
    fig.update_traces(texttemplate="%{text:.1f}",textposition="top center"); st.plotly_chart(tema(fig),width="stretch")
with b:
    energia=df.groupby("PRX_DESCRICAO",as_index=False)[["REAL_CNR_KWH","REAL_INC_KWH"]].sum().melt("PRX_DESCRICAO",var_name="Indicador",value_name="kWh")
    energia["MWh"]=energia["kWh"]/1000; energia["Indicador"]=energia.Indicador.map({"REAL_CNR_KWH":"CNR","REAL_INC_KWH":"Incremento"})
    fig=px.bar(energia,x="PRX_DESCRICAO",y="MWh",color="Indicador",barmode="group",text_auto=".2f",title="Energia por equipe (MWh)")
    fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig),width="stretch")

st.subheader("Base de validação MEPE")
st.dataframe(df.sort_values(["MES_REF","PRX_DESCRICAO"]),width="stretch",hide_index=True)
st.download_button("Baixar validação MEPE",df.to_csv(index=False,sep=";").encode("utf-8-sig"),"validacao_mepe.csv","text/csv",width="stretch")
