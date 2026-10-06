        .fillna("Não informado").replace("", "Não informado")
        .value_counts().head(10).rename_axis("Motivo").reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )
    fig = px.bar(
        motivos, x="Quantidade", y="Motivo", orientation="h",
        title="Principais motivos de não execução",
        color_discrete_sequence=["#F87171"],
        text="Quantidade",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="auto", cliponaxis=False, insidetextanchor="middle")
    st.plotly_chart(tema_figura(fig), width="stretch")

with st.expander("Consultar produção detalhada"):
    detalhe_base = df.copy()
    campos_datahora = {
        "HOST_VI_DT_INI_DESLOCAMENTO": "HORARIO_INICIO_DESLOCAMENTO",
        "HOST_VI_DT_FIM_DESLOCAMENTO": "HORARIO_FIM_DESLOCAMENTO",
        "HOST_VI_DT_INI_SERVICO": "HORARIO_INICIO_SERVICO",
        "HOST_VI_DT_FIM_SERVICO": "HORARIO_FIM_SERVICO",
    }
    datas_convertidas = {}
    for coluna_origem, coluna_horario in campos_datahora.items():
        if coluna_origem in detalhe_base.columns:
            datas_convertidas[coluna_origem] = pd.to_datetime(
                detalhe_base[coluna_origem], errors="coerce", dayfirst=True
            )
            detalhe_base[coluna_horario] = datas_convertidas[
                coluna_origem
            ].dt.strftime("%H:%M:%S").fillna("")
        else:
            datas_convertidas[coluna_origem] = pd.Series(
                pd.NaT, index=detalhe_base.index, dtype="datetime64[ns]"
            )
            detalhe_base[coluna_horario] = ""

    detalhe_base["TEMPO_DESLOCAMENTO"] = formatar_duracao(
        datas_convertidas["HOST_VI_DT_INI_DESLOCAMENTO"],
        datas_convertidas["HOST_VI_DT_FIM_DESLOCAMENTO"],
    )
    detalhe_base["TEMPO_SERVICO"] = formatar_duracao(
        datas_convertidas["HOST_VI_DT_INI_SERVICO"],
        datas_convertidas["HOST_VI_DT_FIM_SERVICO"],
    )

    colunas_tabela = [
        "NR_OS", "DT_CONCLUSAO", "REGIONAL_PAINEL", "GRUPOS",
        "PRX_DESCRICAO", "EMP_SIGLA", "projeto_perdas",
        "RESULTADO_INSPECAO_1", "CODIGO_IRREGULARIDADE_CAMPO",
        "MOTIVO_NAO_EXECUTADO", "NOME_MUNICIPIO", "UC",
        "HORARIO_INICIO_DESLOCAMENTO", "HORARIO_FIM_DESLOCAMENTO",
        "TEMPO_DESLOCAMENTO", "HORARIO_INICIO_SERVICO",
        "HORARIO_FIM_SERVICO", "TEMPO_SERVICO",
    ]
    colunas_tabela = [c for c in colunas_tabela if c in detalhe_base.columns]
    detalhe = detalhe_base[colunas_tabela].sort_values(
        "DT_CONCLUSAO", ascending=False
    )
    detalhe = detalhe.rename(columns={
        "HORARIO_INICIO_DESLOCAMENTO": "Horário início deslocamento",
        "HORARIO_FIM_DESLOCAMENTO": "Horário fim deslocamento",
        "TEMPO_DESLOCAMENTO": "Tempo deslocamento",
        "HORARIO_INICIO_SERVICO": "Horário início serviço",
        "HORARIO_FIM_SERVICO": "Horário fim serviço",
        "TEMPO_SERVICO": "Tempo serviço",
    })
    st.dataframe(detalhe, width="stretch", hide_index=True, height=430)
    st.download_button(
        "Baixar seleção em CSV",
        detalhe.to_csv(index=False, sep=";", encoding="utf-8-sig"),
        file_name=(
            f"producao_{meses[0]:02d}_a_{meses[-1]:02d}_2026.csv"
            if len(meses) > 1
            else f"producao_{MESES[meses[0]].lower()}_2026.csv"
        ),
        mime="text/csv",
    )

horario_atualizacao = None
if "ATUALIZADO_EM" in producao.columns:
    horarios_base = pd.to_datetime(
        producao["ATUALIZADO_EM"], errors="coerce", utc=True
    ).dropna()
    if not horarios_base.empty:
        horario_atualizacao = horarios_base.max().tz_convert(
            "America/Sao_Paulo"
        ).to_pydatetime()

# O arquivo pode ter sido substituído no GitHub/Streamlit mesmo quando uma
# versão antiga da coluna ATUALIZADO_EM permaneceu dentro do parquet. Nesse
# caso, considera também a modificação real do arquivo e mostra a data mais
# recente entre as duas fontes.
horario_arquivo = datetime.fromtimestamp(
    ARQ_PRODUCAO.stat().st_mtime,
    tz=ZoneInfo("America/Sao_Paulo"),
)
if horario_atualizacao is None or horario_arquivo > horario_atualizacao:
    horario_atualizacao = horario_arquivo

st.caption(
    f"Dados atualizados em: {horario_atualizacao:%d/%m/%Y às %H:%M} · "
    "Fonte: ODS de produção · Data de referência: DT_CONCLUSAO · "
    "Rio Verde e Morrinhos definidos pela coluna POLO."
)
