from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MEPE", page_icon="🎯", layout="wide")
BASE = Path(__file__).resolve().parents[1]
ARQ = BASE / "dados" / "mepe.parquet"
MESES = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

def numero(v, casas=2): return f"{v:,.{casas}f}".replace(",","X").replace(".",",").replace("X",".")
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
