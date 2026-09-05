from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MEPE", page_icon="🎯", layout="wide")
BASE = Path(__file__).resolve().parents[1]
ARQ = BASE / "dados" / "mepe.parquet"
ARQ_VALIDACAO = BASE / "dados" / "mepe_validacao_final.parquet"
MESES = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

def numero(v, casas=2): return f"{v:,.{casas}f}".replace(",","X").replace(".",",").replace("X",".")
def tema(fig, h=420):
    fig.update_layout(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#CAD5E2",legend_title_text="",legend=dict(orientation="h",x=.5,xanchor="center",y=1.04,yanchor="bottom"),margin=dict(l=25,r=50,t=90,b=45))
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)",automargin=True)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)",automargin=True)
    return fig

st.markdown("""<style>.stApp{background:#07111F;color:#E8EEF6}[data-testid="stSidebar"]{background:#0B1728;border-right:1px solid #1E3047}[data-testid="stSidebarNav"]{display:none}.block-container{padding-top:1.5rem;max-width:1550px}div[data-testid="stMetric"],div[data-testid="stPlotlyChart"]{background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:.5rem}.nav{display:block;padding:.55rem;margin:.25rem 0;border:1px solid #46556A;border-radius:.5rem;text-align:center;color:white!important;text-decoration:none!important}</style>""",unsafe_allow_html=True)
if not ARQ.is_file():
    st.error("Base MEPE não encontrada."); st.info("Execute o Atualizador Único V16 para gerar dados/mepe.parquet."); st.stop()

@st.cache_data(ttl=900)
def carregar(): return pd.read_parquet(ARQ)
df0 = carregar()
with st.sidebar:
    st.markdown("### 🎯 MEPE"); st.caption("Recuperação de Energia · Sul")
    st.markdown('<a class="nav" href="/" target="_self">📊 Produção</a>',unsafe_allow_html=True)
    for arq,label,icone in [("2_Energia_CNR.py","Energia CNR","⚡"),("3_Incremento.py","Incremento","📈")]:
        if (BASE/"pages"/arq).is_file():
            st.page_link(f"pages/{arq}",label=label,icon=icone,width="stretch")
    st.button("🎯 MEPE",disabled=True,width="stretch")
    if (BASE/"pages"/"5_CAPEX_OPEX.py").is_file():
        st.page_link("pages/5_CAPEX_OPEX.py",label="CAPEX e OPEX",icon="💰",width="stretch")
    pagina_turnos = next(
        (nome for nome in ["6_Validacao_Turnos.py", "6_Validacao_turnos.py"] if (BASE/"pages"/nome).is_file()),
        None,
    )
    if pagina_turnos:
        st.page_link(f"pages/{pagina_turnos}",label="Validação de Turnos",icon="🕒",width="stretch")
    st.markdown("---")
    regs=st.multiselect("Regional",sorted(df0.REGIONAL_MEPE.unique()),default=sorted(df0.REGIONAL_MEPE.unique()))
    meses=st.multiselect("Mês",sorted(df0.MES_REF.unique()),default=sorted(df0.MES_REF.unique()),format_func=lambda x:MESES[int(x)])
    equipes_disp=sorted(df0.loc[df0.REGIONAL_MEPE.isin(regs),"PRX_DESCRICAO"].unique())
    equipes=st.multiselect("Equipe",equipes_disp,default=equipes_disp,key="equipes_mepe_"+"_".join(regs))
df=df0[df0.REGIONAL_MEPE.isin(regs)&df0.MES_REF.isin(meses)&df0.PRX_DESCRICAO.isin(equipes)].copy()
atualizado=pd.to_datetime(df0.get("ATUALIZADO_EM",pd.Series(dtype=str)),errors="coerce").max()
st.title("MEPE"); st.caption(f"{len(df):,.0f} combinações de equipe e mês filtradas · Dados atualizados em: {atualizado:%d/%m/%Y às %H:%M}" if pd.notna(atualizado) else f"{len(df):,.0f} combinações filtradas".replace(",","."))
def classe(pontos, indicador):
    limites={"UPS":(20,15.2,8.2),"CNR":(30,22.8,12),"INCREMENTO":(50,37.5,20),"FINAL":(100,76,41)}[indicador]
    if indicador=="FINAL" and pontos==0: return "Sem classe"
    return "Classe A" if pontos>=limites[0] else "Classe B" if pontos>=limites[1] else "Classe C" if pontos>=limites[2] else "Classe D"

resumo=df.groupby(["REGIONAL_MEPE","PRX_DESCRICAO"],as_index=False).agg(
    META_UPS=("META_UPS_PONT","sum"),REAL_UPS=("REAL_UPS_PONT","sum"),
    META_CNR=("META_CNR_KWH","sum"),REAL_CNR=("REAL_CNR_KWH","sum"),
    META_INC=("META_INC_KWH","sum"),REAL_INC=("REAL_INC_KWH","sum"),
)
resumo["PONT_UPS"]=(resumo.REAL_UPS/resumo.META_UPS.replace(0,pd.NA)*20).fillna(0).clip(upper=20)
resumo["PONT_CNR"]=(resumo.REAL_CNR/resumo.META_CNR.replace(0,pd.NA)*30).fillna(0)
resumo["PONT_INC"]=(resumo.REAL_INC/resumo.META_INC.replace(0,pd.NA)*50).fillna(0).clip(upper=50)
resumo["PONT_TOTAL"]=resumo[["PONT_UPS","PONT_CNR","PONT_INC"]].sum(axis=1)
resumo["CLASSE_FINAL"]=resumo.PONT_TOTAL.map(lambda v:classe(v,"FINAL"))
percentual_ab=resumo.CLASSE_FINAL.isin(["Classe A","Classe B"]).mean()*100 if len(resumo) else 0
c1,c2,c3,c4=st.columns(4); c1.metric("Equipes avaliadas",len(resumo)); c2.metric("Média da pontuação",numero(resumo.PONT_TOTAL.mean() if len(resumo) else 0)); c3.metric("Equipes Classe A+B",f"{numero(percentual_ab,1)}%"); c4.metric("Maior pontuação",numero(resumo.PONT_TOTAL.max() if len(resumo) else 0))

long=resumo.melt(id_vars=["PRX_DESCRICAO"],value_vars=["PONT_UPS","PONT_CNR","PONT_INC"],var_name="Indicador",value_name="Pontos")
long["Indicador"]=long["Indicador"].map({"PONT_UPS":"UPS","PONT_CNR":"CNR","PONT_INC":"Incremento"})
fig=px.bar(long,x="PRX_DESCRICAO",y="Pontos",color="Indicador",barmode="stack",text_auto=".1f",title="Pontuação MEPE por equipe",color_discrete_map={"UPS":"#38BDF8","CNR":"#F59E0B","Incremento":"#34D399"})
fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig,500),width="stretch")

cores_classe={"Classe A":"background-color:#166534;color:white","Classe B":"background-color:#CA8A04;color:white","Classe C":"background-color:#EA580C;color:white","Classe D":"background-color:#B91C1C;color:white"}
def tabela_indicador(nome,meta,real,pont):
    t=resumo[["PRX_DESCRICAO",meta,real,pont]].copy()
    t["CLASSIFICAÇÃO"]=t[pont].map(lambda v:classe(v,nome))
    if nome in {"CNR","INCREMENTO"}:
        t[meta]=t[meta].map(lambda v:f"{v:,.0f}".replace(",","."))
        t[real]=t[real].map(lambda v:f"{v:,.0f}".replace(",","."))
        t=t.rename(columns={meta:"META (kWh)",real:"REALIZADO (kWh)",pont:"PONTUAÇÃO","PRX_DESCRICAO":"EQUIPE"})
    else:
        t=t.rename(columns={meta:"META",real:"REALIZADO",pont:"PONTUAÇÃO","PRX_DESCRICAO":"EQUIPE"})
    return t.round(2)

st.subheader("Resultado por indicador")
aba_ups,aba_cnr,aba_inc,aba_final=st.tabs(["UPS","CNR","Incremento","Classificação final"])
with aba_ups:
    t_ups=tabela_indicador("UPS","META_UPS","REAL_UPS","PONT_UPS"); st.dataframe(t_ups.style.map(lambda v:cores_classe.get(v,""),subset=["CLASSIFICAÇÃO"]),width="stretch",hide_index=True)
with aba_cnr:
    t_cnr=tabela_indicador("CNR","META_CNR","REAL_CNR","PONT_CNR"); st.dataframe(t_cnr.style.map(lambda v:cores_classe.get(v,""),subset=["CLASSIFICAÇÃO"]),width="stretch",hide_index=True)
with aba_inc:
    t_inc=tabela_indicador("INCREMENTO","META_INC","REAL_INC","PONT_INC"); st.dataframe(t_inc.style.map(lambda v:cores_classe.get(v,""),subset=["CLASSIFICAÇÃO"]),width="stretch",hide_index=True)
with aba_final:
    classificacao=resumo[["REGIONAL_MEPE","PRX_DESCRICAO","PONT_UPS","PONT_CNR","PONT_INC","PONT_TOTAL","CLASSE_FINAL"]].rename(columns={"REGIONAL_MEPE":"REGIONAL","PRX_DESCRICAO":"EQUIPE","PONT_UPS":"UPS","PONT_CNR":"CNR","PONT_INC":"INCREMENTO","PONT_TOTAL":"TOTAL","CLASSE_FINAL":"CLASSIFICAÇÃO"}).round(2)
    st.dataframe(classificacao.style.map(lambda v:cores_classe.get(v,""),subset=["CLASSIFICAÇÃO"]),width="stretch",hide_index=True)

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

st.subheader("Base de validação MEPE por TOI/SS")
if ARQ_VALIDACAO.is_file():
    validacao=pd.read_parquet(ARQ_VALIDACAO)
    validacao=validacao[validacao.PRX_DESCRICAO.isin(equipes)&validacao.MES_REF.isin(meses)]
else:
    validacao=df.copy()
st.dataframe(validacao.sort_values(["MES_REF","PRX_DESCRICAO"]),width="stretch",hide_index=True)
st.download_button("Baixar validação detalhada",validacao.to_csv(index=False,sep=";").encode("utf-8-sig"),"validacao_mepe_por_toi.csv","text/csv",width="stretch")
