from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CAPEX e OPEX",page_icon="💰",layout="wide")
BASE=Path(__file__).resolve().parents[1]; ARQ=BASE/"dados"/"capex_opex.parquet"
MESES={1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}
def moeda(v): return "R$ "+f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def tema(fig,h=420):
    fig.update_layout(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#CAD5E2",legend_title_text="",legend=dict(orientation="h",x=.5,xanchor="center",y=1.04,yanchor="bottom",entrywidth=.30,entrywidthmode="fraction"),margin=dict(l=25,r=55,t=90,b=45))
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)",automargin=True); fig.update_yaxes(gridcolor="rgba(148,163,184,.10)",automargin=True); return fig
st.markdown("""<style>.stApp{background:#07111F;color:#E8EEF6}[data-testid="stSidebar"]{background:#0B1728;border-right:1px solid #1E3047}[data-testid="stSidebarNav"]{display:none}.block-container{padding-top:1.5rem;max-width:1550px}div[data-testid="stMetric"],div[data-testid="stPlotlyChart"]{background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:.5rem}.nav{display:block;padding:.55rem;margin:.25rem 0;border:1px solid #46556A;border-radius:.5rem;text-align:center;color:white!important;text-decoration:none!important}</style>""",unsafe_allow_html=True)
if not ARQ.is_file(): st.error("Base CAPEX/OPEX não encontrada."); st.info("Execute o Atualizador Único V13."); st.stop()
@st.cache_data(ttl=900)
def carregar():
    d=pd.read_parquet(ARQ); d["DT_CONCLUSAO"]=pd.to_datetime(d["DT_CONCLUSAO"],errors="coerce"); return d
d0=carregar()
with st.sidebar:
    st.markdown("### 💰 CAPEX e OPEX"); st.caption("Somente equipes RIOF e MORF")
    st.markdown('<a class="nav" href="/" target="_self">📊 Produção</a>',unsafe_allow_html=True)
    for a,l,i in [("2_Energia_CNR.py","Energia CNR","⚡"),("3_Incremento.py","Incremento","📈"),("4_MEPE.py","MEPE","🎯")]:
        st.page_link(f"pages/{a}",label=l,icon=i,width="stretch")
    st.button("💰 CAPEX e OPEX",disabled=True,width="stretch")
    st.page_link("pages/6_Validacao_Turnos.py",label="Validação de Turnos",icon="🕒",width="stretch")
    st.markdown("---")
    regs=st.multiselect("Regional",sorted(d0.REGIONAL.unique()),default=sorted(d0.REGIONAL.unique()))
    meses=st.multiselect("Mês",sorted(d0.MES_REF.unique()),default=sorted(d0.MES_REF.unique()),format_func=lambda x:MESES[int(x)])
    equipes_disp=sorted(d0.loc[d0.REGIONAL.isin(regs),"EQUIPE"].unique())
    equipes=st.multiselect("Equipe",equipes_disp,default=equipes_disp,key="equipes_capex_"+"_".join(regs))
d=d0[d0.REGIONAL.isin(regs)&d0.MES_REF.isin(meses)&d0.EQUIPE.isin(equipes)].copy()
tot=d.groupby("CLASSIFICACAO").VALOR.sum(); odi=float(tot.get("ODI",0)); odd=float(tot.get("ODD",0)); opex=float(tot.get("OPEX",0)); capex=odi+odd
atualizado=pd.to_datetime(d0.get("ATUALIZADO_EM",pd.Series(dtype=str)),errors="coerce").max()
st.title("CAPEX e OPEX"); st.caption(f"Período pela DT_CONCLUSAO · CAPEX = ODI + ODD · Dados atualizados em: {atualizado:%d/%m/%Y às %H:%M}" if pd.notna(atualizado) else "Período pela DT_CONCLUSAO · CAPEX = ODI + ODD")
c1,c2,c3,c4=st.columns(4); c1.metric("CAPEX",moeda(capex)); c2.metric("ODI",moeda(odi)); c3.metric("ODD",moeda(odd)); c4.metric("OPEX",moeda(opex))
base_total=capex+opex; pcap=capex/base_total*100 if base_total else 0; popex=opex/base_total*100 if base_total else 0
p1,p2,p3=st.columns(3); p1.metric("% CAPEX",f"{pcap:.1f}%".replace(".",",")); p2.metric("% OPEX",f"{popex:.1f}%".replace(".",",")); p3.metric("Lançamentos",f"{len(d):,}".replace(",","."))
a,b=st.columns(2)
with a:
    comp=pd.DataFrame({"Classificação":["ODI","ODD","OPEX"],"Valor":[odi,odd,opex]}); comp["Rótulo"]=comp.Valor.map(moeda)
    fig=px.bar(comp,x="Classificação",y="Valor",color="Classificação",text="Rótulo",title="Composição dos custos",color_discrete_map={"ODI":"#38BDF8","ODD":"#A78BFA","OPEX":"#F59E0B"}); fig.update_traces(textposition="auto",cliponaxis=False,showlegend=False); st.plotly_chart(tema(fig),width="stretch")
with b:
    mensal=d.groupby(["MES_REF","CLASSIFICACAO"],as_index=False).VALOR.sum(); mensal["Mês"]=mensal.MES_REF.map(MESES); mensal["Rótulo"]=mensal.VALOR.map(moeda)
    fig=px.bar(mensal,x="Mês",y="VALOR",color="CLASSIFICACAO",barmode="stack",text="Rótulo",title="Evolução mensal"); fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig),width="stretch")
a,b=st.columns(2)
with a:
    serv=d.groupby(["TIPO_SERVICO","CLASSIFICACAO"],as_index=False).agg(Valor=("VALOR","sum"),Quantidade=("QTD","sum")).sort_values("Valor")
    fig=px.bar(serv,x="Valor",y="TIPO_SERVICO",orientation="h",color="CLASSIFICACAO",text="Quantidade",title="Serviços que compõem os custos"); fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig),width="stretch")
with b:
    eq=d.groupby(["EQUIPE","CLASSIFICACAO"],as_index=False).VALOR.sum(); fig=px.bar(eq,x="EQUIPE",y="VALOR",color="CLASSIFICACAO",barmode="stack",title="Custos por equipe"); fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig),width="stretch")
st.subheader("Base de validação CAPEX/OPEX"); st.dataframe(d.sort_values("DT_CONCLUSAO",ascending=False),width="stretch",hide_index=True)
st.download_button("Baixar base de validação",d.to_csv(index=False,sep=";").encode("utf-8-sig"),"validacao_capex_opex.csv","text/csv",width="stretch")
