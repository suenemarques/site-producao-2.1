from pathlib import Path
from calendar import monthrange
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Validação de Turnos",page_icon="🕒",layout="wide")
BASE=Path(__file__).resolve().parents[1]; ARQ=BASE/"dados"/"validacao_turnos.parquet"; METAS=BASE/"METAS 2026.xlsx"
MESES={1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}
def inteiro(v): return f"{v:,.0f}".replace(",",".")
def tema(fig,h=430):
    fig.update_layout(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#CAD5E2",legend_title_text="",legend=dict(orientation="h",x=.5,xanchor="center",y=1.04,yanchor="bottom"),margin=dict(l=25,r=55,t=90,b=50))
    fig.update_xaxes(gridcolor="rgba(148,163,184,.10)",automargin=True); fig.update_yaxes(gridcolor="rgba(148,163,184,.10)",automargin=True); return fig
st.markdown("""<style>.stApp{background:#07111F;color:#E8EEF6}[data-testid="stSidebar"]{background:#0B1728;border-right:1px solid #1E3047}[data-testid="stSidebarNav"]{display:none}.block-container{padding-top:1.5rem;max-width:1550px}div[data-testid="stMetric"],div[data-testid="stPlotlyChart"]{background:#0D1A2B;border:1px solid #20334A;border-radius:14px;padding:.5rem}.nav{display:block;padding:.55rem;margin:.25rem 0;border:1px solid #46556A;border-radius:.5rem;text-align:center;color:white!important;text-decoration:none!important}</style>""",unsafe_allow_html=True)
if not ARQ.is_file(): st.error("Base de turnos não encontrada."); st.info("Execute o Atualizador Único V15 para gerar dados/validacao_turnos.parquet."); st.stop()
@st.cache_data(ttl=900)
def carregar():
    d=pd.read_parquet(ARQ)
    for c in ["DATA_TURNO","DT_BAIXA","HOST_VI_DT_INI_DESLOCAMENTO","HOST_VI_DT_FIM_DESLOCAMENTO","HOST_VI_DT_INI_SERVICO","HOST_VI_DT_FIM_SERVICO"]: d[c]=pd.to_datetime(d[c],errors="coerce")
    return d
d0=carregar(); meses_disp=sorted(d0.DATA_TURNO.dt.month.dropna().astype(int).unique())
with st.sidebar:
    st.markdown("### 🕒 Validação de Turnos"); st.caption("Recuperação de Energia · Sul")
    st.markdown('<a class="nav" href="/" target="_self">📊 Produção</a>',unsafe_allow_html=True)
    for a,l,i in [("2_Energia_CNR.py","Energia CNR","⚡"),("3_Incremento.py","Incremento","📈"),("4_MEPE.py","MEPE","🎯"),("5_CAPEX_OPEX.py","CAPEX e OPEX","💰")]:
        st.page_link(f"pages/{a}",label=l,icon=i,width="stretch")
    st.button("🕒 Validação de Turnos",disabled=True,width="stretch"); st.markdown("---")
    regs=st.multiselect("Regional",sorted(d0.REGIONAL_TURNO.unique()),default=sorted(d0.REGIONAL_TURNO.unique()))
    mes=st.selectbox("Mês",meses_disp,index=len(meses_disp)-1,format_func=lambda x:MESES[x])
    inicio_padrao=pd.Timestamp(2026,mes,1).date(); fim_padrao=pd.Timestamp(2026,mes,monthrange(2026,mes)[1]).date()
    periodo=st.date_input("Período",value=(inicio_padrao,fim_padrao),min_value=inicio_padrao,max_value=fim_padrao,format="DD/MM/YYYY")
    equipes_disp=sorted(d0[d0.REGIONAL_TURNO.isin(regs)].PRX_DESCRICAO.unique()); equipes=st.multiselect("Equipe",equipes_disp,default=equipes_disp)
ini=pd.Timestamp(periodo[0] if isinstance(periodo,(tuple,list)) else periodo); fim=pd.Timestamp(periodo[-1] if isinstance(periodo,(tuple,list)) else periodo)+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1)
d=d0[d0.REGIONAL_TURNO.isin(regs)&d0.PRX_DESCRICAO.isin(equipes)&d0.DATA_TURNO.between(ini,fim)].copy()

# Primeiro início e último fim por equipe/dia; almoço: RV 1h, Morrinhos 1h12.
d["INICIO_EFETIVO"]=d[["HOST_VI_DT_INI_DESLOCAMENTO","HOST_VI_DT_INI_SERVICO"]].min(axis=1)
d["FIM_EFETIVO"]=d[["HOST_VI_DT_FIM_SERVICO","HOST_VI_DT_FIM_DESLOCAMENTO"]].max(axis=1)
diario=d.groupby(["REGIONAL_TURNO","PRX_DESCRICAO","DATA_TURNO"],as_index=False).agg(INICIO=("INICIO_EFETIVO","min"),FIM=("FIM_EFETIVO","max"),SS=("NR_OS","nunique"))
diario=diario[diario.INICIO.dt.date.eq(diario.FIM.dt.date)].copy()
diario["DESCONTO_ALMOCO"]=diario.REGIONAL_TURNO.map({"RIO VERDE":1.0,"MORRINHOS":1.2})
diario["HORAS"]=[max((f-i).total_seconds()/3600-desc,0) for i,f,desc in zip(diario.INICIO,diario.FIM,diario.DESCONTO_ALMOCO)]
resumo=diario.groupby(["REGIONAL_TURNO","PRX_DESCRICAO"],as_index=False).agg(Dias=("DATA_TURNO","nunique"),Horas=("HORAS","sum"),SS=("SS","sum")); resumo["Meta horas"]=resumo.Dias*8; resumo["Média diária"]=resumo.Horas/resumo.Dias.replace(0,pd.NA); resumo["Situação"]=resumo.apply(lambda r:"Dentro do esperado" if r.Horas>=r["Meta horas"] else "Abaixo do esperado",axis=1)
atualizado=pd.to_datetime(d0.get("ATUALIZADO_EM",pd.Series(dtype=str)),errors="coerce").max()
st.title("Validação de Turnos"); st.caption(f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y} · primeiro início ao último fim por equipe/dia · Dados atualizados em: {atualizado:%d/%m/%Y às %H:%M}" if pd.notna(atualizado) else f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}")
c1,c2,c3,c4=st.columns(4); horas=float(resumo.Horas.sum()); meta=float(resumo["Meta horas"].sum()); c1.metric("Horas realizadas",f"{horas:,.1f} h".replace(",","X").replace(".",",").replace("X",".")); c2.metric("Meta de horas",f"{meta:,.1f} h".replace(",","X").replace(".",",").replace("X",".")); c3.metric("Dias-equipe",inteiro(resumo.Dias.sum())); c4.metric("SS executadas",inteiro(d.NR_OS.nunique()))
comp=resumo.melt(id_vars=["PRX_DESCRICAO","Situação"],value_vars=["Meta horas","Horas"],var_name="Tipo",value_name="Quantidade")
fig=px.bar(comp,x="PRX_DESCRICAO",y="Quantidade",color="Tipo",barmode="group",text_auto=".1f",title="Meta x realizado de horas por equipe",category_orders={"Tipo":["Meta horas","Horas"]},color_discrete_map={"Meta horas":"#64748B","Horas":"#38BDF8"}); fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig,500),width="stretch")
a,b=st.columns(2)
with a:
    fig=px.bar(resumo,x="PRX_DESCRICAO",y="Média diária",color="Situação",text_auto=".1f",title="Média diária por equipe",color_discrete_map={"Dentro do esperado":"#34D399","Abaixo do esperado":"#F87171"}); fig.add_hline(y=8,line_dash="dash",line_color="#F59E0B",annotation_text="Meta 8h"); fig.update_traces(textposition="auto",cliponaxis=False); st.plotly_chart(tema(fig),width="stretch")
with b:
    linha=diario.groupby("DATA_TURNO",as_index=False).HORAS.sum(); fig=px.line(linha,x="DATA_TURNO",y="HORAS",markers=True,text="HORAS",title="Horas trabalhadas por dia"); fig.update_traces(texttemplate="%{text:.1f}",textposition="top center"); st.plotly_chart(tema(fig),width="stretch")
st.subheader("Resumo por equipe"); st.dataframe(resumo,width="stretch",hide_index=True)
st.subheader("Base por SS"); st.dataframe(d.sort_values(["DATA_TURNO","PRX_DESCRICAO"]),width="stretch",hide_index=True)
st.download_button("Baixar Base por SS",d.to_csv(index=False,sep=";").encode("utf-8-sig"),"validacao_turnos_base_ss.csv","text/csv",width="stretch")
