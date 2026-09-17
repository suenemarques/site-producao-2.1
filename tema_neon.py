import streamlit as st


PAGINAS_PAINEL = [
    ("producao", "app.py", "Produção", "📊"),
    ("cnr", "pages/2_Energia_CNR.py", "Energia CNR", "⚡"),
    ("incremento", "pages/3_Incremento.py", "Incremento", "📈"),
    ("mepe", "pages/4_MEPE.py", "MEPE", "🎯"),
    ("capex", "pages/5_CAPEX_OPEX.py", "CAPEX e OPEX", "💰"),
    ("turnos", "pages/6_Validacao_turnos.py", "Validação de Turnos", "🕒"),
]


def menu_lateral(pagina_atual: str) -> None:
    """Exibe o mesmo menu em todas as páginas, preservando a sessão."""
    st.markdown("### ⚡ Produção 2.0")
    st.caption("Recuperação de Energia · Sul")
    for chave, caminho, rotulo, icone in PAGINAS_PAINEL:
        if chave == pagina_atual:
            st.button(f"{icone} {rotulo}", disabled=True, width="stretch", key=f"menu_{chave}")
        else:
            st.page_link(caminho, label=rotulo, icon=icone, width="stretch")


def aplicar_tema_neon() -> None:
    """Aplica o fundo animado compartilhado em todas as páginas do painel."""
    st.markdown(
        """
        <style>
        .stApp {
          background:
            radial-gradient(circle at 18% 18%, rgba(14,165,233,.10), transparent 28%),
            radial-gradient(circle at 82% 72%, rgba(52,211,153,.07), transparent 30%),
            #07111F !important;
          color:#E8EEF6;
          isolation:isolate;
          overflow-x:hidden;
        }
        .stApp::before,.stApp::after {
          content:"";
          position:fixed;
          inset:-22%;
          pointer-events:none;
          z-index:0;
          background-repeat:repeat;
          will-change:transform;
        }
        .stApp::before {
          opacity:.38;
          background-size:260px 220px;
          background-image:
            radial-gradient(circle at 20px 22px,rgba(56,189,248,.95) 0 2px,transparent 3px),
            radial-gradient(circle at 142px 72px,rgba(52,211,153,.72) 0 1.7px,transparent 2.8px),
            radial-gradient(circle at 224px 176px,rgba(56,189,248,.78) 0 1.8px,transparent 2.8px),
            linear-gradient(28deg,transparent 48.9%,rgba(56,189,248,.22) 49.4%,rgba(56,189,248,.22) 50.1%,transparent 50.6%),
            linear-gradient(146deg,transparent 49%,rgba(52,211,153,.16) 49.5%,rgba(52,211,153,.16) 50.1%,transparent 50.6%);
          filter:drop-shadow(0 0 5px rgba(56,189,248,.45));
          animation:rede-neon-flutuar 28s linear infinite;
        }
        .stApp::after {
          opacity:.20;
          background-size:340px 285px;
          background-image:
            radial-gradient(circle at 64px 54px,rgba(14,165,233,.9) 0 1.6px,transparent 2.7px),
            radial-gradient(circle at 265px 205px,rgba(45,212,191,.75) 0 1.8px,transparent 2.8px),
            linear-gradient(118deg,transparent 49.1%,rgba(14,165,233,.18) 49.6%,rgba(14,165,233,.18) 50.1%,transparent 50.6%),
            linear-gradient(18deg,transparent 49.1%,rgba(45,212,191,.13) 49.6%,rgba(45,212,191,.13) 50.1%,transparent 50.6%);
          filter:blur(.2px) drop-shadow(0 0 8px rgba(14,165,233,.40));
          animation:rede-neon-derivar 38s linear infinite;
        }
        @keyframes rede-neon-flutuar {
          0%{transform:translate3d(-2%,-3%,0) rotate(0deg)}
          50%{transform:translate3d(7%,5%,0) rotate(.8deg)}
          100%{transform:translate3d(18%,12%,0) rotate(1.5deg)}
        }
        @keyframes rede-neon-derivar {
          0%{transform:translate3d(8%,6%,0) rotate(1deg) scale(1.03)}
          50%{transform:translate3d(0%,-2%,0) rotate(0deg) scale(1)}
          100%{transform:translate3d(-12%,-10%,0) rotate(-1deg) scale(1.03)}
        }
        @media (prefers-reduced-motion:reduce) {
          .stApp::before,.stApp::after{animation:none}
        }
        .stApp>*{position:relative;z-index:1}
        [data-testid="stSidebar"] {
          background:rgba(11,23,40,.94)!important;
          backdrop-filter:blur(14px);
          border-right:1px solid rgba(56,189,248,.20)!important;
          box-shadow:10px 0 35px rgba(0,0,0,.18);
        }
        [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"] > div {
          max-height:100vh!important;
          overflow-y:auto!important;
          overflow-x:hidden!important;
          scrollbar-width:thin;
          scrollbar-color:rgba(56,189,248,.55) rgba(11,23,40,.25);
        }
        [data-testid="stHeader"]{background:rgba(7,17,31,.72)!important;backdrop-filter:blur(12px)}
        [data-testid="stToolbar"],
        [data-testid="stHeaderActionElements"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        #MainMenu,
        footer {display:none!important;visibility:hidden!important}
        div[data-testid="stMetric"],div[data-testid="stPlotlyChart"] {
          background:rgba(11,23,40,.88)!important;
          backdrop-filter:blur(10px);
          border-color:rgba(56,189,248,.18)!important;
          box-shadow:0 14px 35px rgba(0,0,0,.20);
          transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease;
        }
        div[data-testid="stMetric"]:hover,div[data-testid="stPlotlyChart"]:hover {
          transform:translateY(-2px);
          border-color:rgba(56,189,248,.35)!important;
          box-shadow:0 18px 42px rgba(0,0,0,.28),0 0 22px rgba(14,165,233,.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
