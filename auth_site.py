from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
ARQUIVOS_USUARIOS = (
    BASE_DIR / "USUARIOS SITE.xlsx",
    BASE_DIR / "SITE DE USUÁRIOS.xlsx",
    BASE_DIR / "SITE DE USUARIOS.xlsx",
)

ACESSOS_VALIDOS = {"GERAL", "RIOF", "MORF"}
PAGINAS_REGIONAIS = {"PRODUCAO", "CNR", "INCREMENTO", "MEPE"}


def _normalizar(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def _localizar_planilha() -> Path:
    for caminho in ARQUIVOS_USUARIOS:
        if caminho.is_file():
            return caminho

    nomes = ", ".join(c.name for c in ARQUIVOS_USUARIOS)
    raise FileNotFoundError(
        f"Planilha de usuários não encontrada. Nomes aceitos: {nomes}"
    )


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_usuarios(
    caminho: str,
    assinatura: tuple[int, int],
) -> dict[str, str]:
    del assinatura

    usuarios = pd.read_excel(caminho)
    usuarios.columns = [_normalizar(c) for c in usuarios.columns]

    obrigatorias = {"LOGIN", "REGIONAL"}
    faltantes = obrigatorias - set(usuarios.columns)
    if faltantes:
        raise KeyError(
            "Planilha de usuários sem a(s) coluna(s): "
            + ", ".join(sorted(faltantes))
        )

    usuarios["LOGIN_N"] = usuarios["LOGIN"].map(_normalizar)
    usuarios["ACESSO_N"] = usuarios["REGIONAL"].map(_normalizar)

    usuarios = usuarios[
        usuarios["LOGIN_N"].ne("")
        & usuarios["ACESSO_N"].isin(ACESSOS_VALIDOS)
    ].drop_duplicates("LOGIN_N", keep="last")

    return dict(zip(usuarios["LOGIN_N"], usuarios["ACESSO_N"]))


def _usuarios_cadastrados() -> dict[str, str]:
    caminho = _localizar_planilha()
    status = caminho.stat()
    return _carregar_usuarios(
        str(caminho),
        (status.st_mtime_ns, status.st_size),
    )


def exigir_login() -> dict[str, str]:
    """Bloqueia a página e retorna LOGIN/ACESSO do usuário autorizado."""
    # Oculta globalmente a barra superior do Streamlit Cloud, incluindo
    # Compartilhar, favorito, editar, GitHub/código-fonte e menu de opções.
    # Como todas as páginas chamam exigir_login(), o ajuste vale no site todo.
    st.markdown(
        """
        <style>
        [data-testid="stToolbar"],
        [data-testid="stAppToolbar"],
        [data-testid="stHeaderActionElements"],
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }

        header a[href*="github.com"],
        a[href*="github.com/suenemarques/site-producao-2.1"] {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        usuarios = _usuarios_cadastrados()
    except Exception as erro:
        st.error(f"Não foi possível carregar os usuários: {erro}")
        st.stop()

    login_sessao = _normalizar(st.session_state.get("usuario_login", ""))
    acesso_sessao = usuarios.get(login_sessao)

    if not acesso_sessao:
        st.session_state.pop("usuario_login", None)
        st.session_state.pop("usuario_acesso", None)

        st.markdown("## Acesso ao painel")
        st.caption("Informe o login cadastrado na planilha de usuários.")

        with st.form("form_login", clear_on_submit=False):
            login_digitado = st.text_input(
                "Usuário",
                placeholder="Ex.: Suene.silva",
            )
            entrar = st.form_submit_button("Entrar", width="stretch")

        if entrar:
            login_n = _normalizar(login_digitado)
            acesso = usuarios.get(login_n)

            if acesso:
                st.session_state["usuario_login"] = login_n
                st.session_state["usuario_acesso"] = acesso
                st.rerun()

            st.error("Usuário não cadastrado ou sem acesso liberado.")

        st.stop()

    st.session_state["usuario_acesso"] = acesso_sessao

    with st.sidebar:
        st.caption(f"Usuário: {login_sessao}")
        st.caption(f"Acesso: {acesso_sessao}")

        if st.button("Sair", key="sair_do_painel", width="stretch"):
            st.session_state.pop("usuario_login", None)
            st.session_state.pop("usuario_acesso", None)
            st.rerun()

        st.markdown("---")

    return {
        "LOGIN": login_sessao,
        "ACESSO": acesso_sessao,
    }


def acesso_geral(usuario: dict[str, str]) -> bool:
    """Retorna True somente para usuários com acesso GERAL."""
    return _normalizar(usuario.get("ACESSO", "")) == "GERAL"


def pode_acessar_pagina(
    usuario: dict[str, str],
    pagina: str,
) -> bool:
    """
    Verifica se a página deve aparecer no menu.

    RIOF e MORF podem acessar somente Produção, CNR, Incremento e MEPE.
    GERAL pode acessar todas as páginas.
    """
    if acesso_geral(usuario):
        return True

    pagina_n = _normalizar(pagina)
    return pagina_n in PAGINAS_REGIONAIS


def exigir_acesso_geral(usuario: dict[str, str]) -> None:
    """
    Bloqueia páginas administrativas para usuários RIOF e MORF.

    Esta validação deve ser executada dentro de cada página restrita.
    Ocultar apenas o link do menu não impede acesso direto pela URL.
    """
    if acesso_geral(usuario):
        return

    st.error("🔒 Você não possui permissão para acessar esta página.")
    st.info(
        "Seu acesso está limitado às páginas Produção, Energia CNR, "
        "Incremento e MEPE."
    )

    if st.button(
        "Voltar para Produção",
        key="voltar_producao_acesso_negado",
        width="stretch",
    ):
        st.switch_page("app.py")

    st.stop()


def filtrar_por_acesso(
    dados: pd.DataFrame,
    coluna_regional: str,
    acesso: str,
) -> pd.DataFrame:
    """Aplica a autorização antes de filtros, indicadores e downloads."""
    acesso_n = _normalizar(acesso)

    if acesso_n == "GERAL":
        return dados.copy()

    if coluna_regional not in dados.columns:
        raise KeyError(f"Coluna regional não encontrada: {coluna_regional}")

    regional = dados[coluna_regional].map(_normalizar)

    if acesso_n == "RIOF":
        permitido = (
            regional.str.contains("RIO VERDE", na=False)
            | regional.str.startswith("RIOF")
        )
    elif acesso_n == "MORF":
        permitido = (
            regional.str.contains("MORRINHOS", na=False)
            | regional.str.startswith("MORF")
        )
    else:
        permitido = pd.Series(False, index=dados.index)

    return dados.loc[permitido].copy()
