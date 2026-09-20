"""Frete Estratégico em Dados — Hackathon Unimar Tech Summit 2026 (Grupo 08).

Executar:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Frete Estratégico · Sisfrete · Grupo 08",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import dados  # noqa: E402  (precisa vir depois do set_page_config)
import graficos  # noqa: E402
import tema  # noqa: E402
from tema import esc, fmt_brl, fmt_compacto, fmt_dec, fmt_int, fmt_pct  # noqa: E402

tema.injetar_css()
tema.cabecalho()


def parar_com_erro(mensagem: str) -> None:
    tema.destaque(f"<b>Não foi possível carregar os dados.</b> {esc(mensagem)}", alerta=True)
    st.stop()


# ============================================================
# CREDENCIAIS E DADOS BÁSICOS
# ============================================================

if not dados.credenciais_ok():
    parar_com_erro(
        "Credenciais não encontradas. Crie um arquivo .env (use o .env.example como modelo) "
        "com SISFRETE_USUARIO e SISFRETE_SENHA."
    )

try:
    with st.spinner("Consultando a rede Sisfrete..."):
        lojas = dados.listar_lojas()
        mercado = dados.resumo_mercado()
except dados.ErroAPI as erro:
    parar_com_erro(str(erro))

if lojas.empty or mercado["total"] == 0:
    parar_com_erro("Nenhuma cotação de setembro de 2026 foi encontrada para esta credencial.")

canais_df = mercado["canais"]
janelas_df = mercado["janelas"]
cidades_df = mercado["cidades"]


# ============================================================
# HERO
# ============================================================

tema.hero(
    "em Dados",
    "Onde a operação de frete ganha — ou perde — a venda? Partimos da visão da rede em setembro, "
    "aproximamos uma loja e comparamos, cotação a cotação, preço, prazo e cobertura de cada transportadora.",
    [
        ("Cotações em setembro", fmt_int(mercado["total"]), "horário de Brasília"),
        ("Lojas com cotações", fmt_int(len(lojas)), None),
        ("Canais de venda", str(len(canais_df)), None),
        ("Janela de análise", "7 dias", "cortes fixos a partir de 01/09"),
    ],
)


# ============================================================
# 01 — A REDE EM SETEMBRO
# ============================================================

tema.secao(
    "rede", "01", "A rede em setembro",
    "Qual canal puxa o volume, como o movimento evolui semana a semana e de onde vêm as consultas?",
)

col_a, col_b = st.columns([5, 7], gap="medium")

with col_a:
    with st.container(key="card-canais"):
        tema.titulo_card("Volume de cotações por canal", "Origem do pedido que gerou a consulta de frete.")
        tema.mostrar_grafico(graficos.canais(canais_df))

with col_b:
    with st.container(key="card-evolucao-rede"):
        tema.titulo_card(
            "Evolução em janelas fixas de 7 dias",
            "Cada barra soma 7 dias corridos a partir de 01/09. A janela vazada ainda está recebendo dados.",
        )
        if janelas_df.empty:
            st.info("Sem dados diários para montar as janelas.")
        else:
            tema.mostrar_grafico(graficos.janelas(janelas_df))

with st.container(key="card-cidades"):
    tema.titulo_card("Top 15 cidades de destino", "Cidades que mais concentram consultas de frete no mês.")
    tema.mostrar_grafico(graficos.cidades(cidades_df))

lider = canais_df.sort_values("cotacoes", ascending=False).iloc[0]
frases = [
    f"O canal <b>{esc(lider['canal'])}</b> responde por <b>{fmt_pct(lider['pct'])}</b> das cotações do mês."
]
if not janelas_df.empty:
    pico = janelas_df.loc[janelas_df["media_dia"].idxmax()]
    frases.append(
        f"A janela de <b>{esc(pico['janela'])}</b> teve a maior média diária: "
        f"<b>{fmt_compacto(pico['media_dia'])}</b> cotações por dia."
    )
if not cidades_df.empty:
    parcela = cidades_df["cotacoes"].sum() / mercado["total"] * 100
    frases.append(
        f"As 15 cidades do ranking somam <b>{fmt_pct(parcela)}</b> das cotações; "
        f"<b>{esc(cidades_df.iloc[0]['cidade'])}</b> lidera."
    )
tema.destaque("<ul>" + "".join(f"<li>{f}</li>" for f in frases) + "</ul>")


# ============================================================
# 02 — UMA LOJA EM DETALHE
# ============================================================

tema.secao(
    "loja", "02", "Uma loja em detalhe",
    "Aqui olhamos somente para uma loja, sem misturar clientes: quanto ela cota, por onde vende "
    "e em quais cidades o comprador fica sem nenhuma opção de frete.",
)

lojas_relevantes = lojas[lojas["cotacoes"] >= 1000]
lojas_relevantes = lojas_relevantes if not lojas_relevantes.empty else lojas
volume_por_loja = dict(zip(lojas_relevantes["loja"], lojas_relevantes["cotacoes"]))

seletor_a, seletor_b = st.columns([3, 2], gap="medium")
loja_id = seletor_a.selectbox(
    "Loja analisada",
    list(volume_por_loja.keys()),
    format_func=lambda i: f"Loja {i} · {fmt_int(volume_por_loja[i])} cotações no mês",
)
tamanho_amostra = seletor_b.select_slider(
    "Cotações usadas para comparar transportadoras",
    options=[2000, 5000, 10000],
    value=5000,
    format_func=fmt_int,
    help="Usamos as cotações mais recentes da loja. Quanto maior a amostra, mais preciso e mais lento.",
)

try:
    with st.spinner(f"Analisando a loja {loja_id}..."):
        loja = dados.analisar_loja(int(loja_id), int(tamanho_amostra))
except dados.ErroAPI as erro:
    parar_com_erro(str(erro))

if loja["total"] == 0:
    st.info("Esta loja não tem cotações em setembro.")
    st.stop()

opcoes = loja["opcoes"]
analise = dados.analisar_transportadoras(opcoes)
pct_com_opcao = loja["com_opcao"] / loja["total"] * 100
sem_opcao_total = loja["total"] - loja["com_opcao"]

tema.indicadores(
    [
        ("Cotações no mês", fmt_int(loja["total"]), f"Loja {loja['loja']}"),
        (
            "Com opção de frete",
            fmt_pct(pct_com_opcao, 1),
            f"{fmt_int(sem_opcao_total)} cotações sem nenhuma opção",
        ),
        (
            "Transportadoras que responderam",
            str(analise["n_transportadoras"]) if analise else "—",
            f"nas {fmt_int(loja['docs_amostra'])} cotações mais recentes",
        ),
        (
            "Frete mais barato (médio)",
            fmt_brl(analise["frete_minimo_medio"]) if analise else "—",
            "total da opção de menor preço",
        ),
    ]
)

evo_col, canal_col = st.columns([7, 5], gap="medium")

with evo_col:
    with st.container(key="card-evolucao-loja"):
        tema.titulo_card(
            "Cotações da loja por janela de 7 dias",
            "Mesmo corte da rede (a partir de 01/09); janela vazada = ainda em andamento.",
        )
        if loja["janelas"].empty:
            st.info("Sem dados diários para montar as janelas.")
        else:
            tema.mostrar_grafico(graficos.janelas(loja["janelas"]))

with canal_col:
    with st.container(key="card-canais-loja"):
        tema.titulo_card("Canais de venda da loja")
        if len(loja["canais"]) >= 2:
            tema.mostrar_grafico(graficos.canais(loja["canais"]))
        elif len(loja["canais"]) == 1:
            unico = loja["canais"].iloc[0]
            tema.destaque(
                f"Esta loja cota apenas pelo canal <b>{esc(unico['canal'])}</b> — "
                "não há comparação de canais a fazer."
            )
        else:
            st.info("A API não retornou o canal de venda para esta loja.")

# ---- Cobertura: onde a loja perde venda ----
cob = loja["cidades"]
cob_visivel = cob[(cob["sem_opcao"] > 0) & (cob["cotacoes"] >= 30)].sort_values(
    "sem_opcao", ascending=False
).head(10)

with st.container(key="card-cobertura"):
    tema.titulo_card(
        "Onde a loja pode estar perdendo venda",
        "Cotações em que nenhuma transportadora devolveu opção de frete, por cidade de destino. "
        "Sem opção de frete, o comprador não consegue fechar a compra.",
    )
    if sem_opcao_total == 0:
        tema.destaque(
            "Todas as cotações do mês retornaram <b>pelo menos uma opção de frete</b>. "
            "Cobertura completa nesta loja."
        )
    elif cob_visivel.empty:
        st.info(
            "Há cotações sem opção de frete, mas espalhadas em cidades com pouco volume "
            "para um ranking confiável."
        )
    else:
        tema.mostrar_grafico(graficos.cobertura_por_cidade(cob_visivel))
        st.caption("Considera cidades com pelo menos 30 cotações na loja.")


# ============================================================
# 03 — TRANSPORTADORAS
# ============================================================

tema.secao(
    "transportadoras", "03", "Transportadoras: preço, prazo e região",
    "Quem é mais barata? Quem entrega mais rápido? E onde cada uma vence? O cruzamento é feito por "
    "cotação (cada opção com o seu próprio preço e prazo), sem misturar cotações diferentes.",
)

if analise is None:
    st.info(
        "Nas cotações mais recentes desta loja nenhuma transportadora devolveu preço válido. "
        "Escolha outra loja para comparar transportadoras."
    )
else:
    ranking = analise["ranking"]

    g1, g2 = st.columns(2, gap="medium")
    with g1:
        with st.container(key="card-vitorias"):
            tema.titulo_card(
                "Quem ganha mais cotações",
                "Em quantas cotações da loja cada transportadora foi a opção mais barata e a mais rápida.",
            )
            tema.mostrar_grafico(graficos.vitorias_transportadoras(ranking))
    with g2:
        with st.container(key="card-dispersao"):
            tema.titulo_card(
                "Preço × prazo",
                "Cada bolha é uma transportadora; o tamanho mostra em quantas cotações ela respondeu.",
            )
            tema.mostrar_grafico(graficos.preco_x_prazo(ranking))

    with st.container(key="card-tabela-transp"):
        tema.titulo_card(
            "Comparativo das transportadoras",
            "Presença = % das cotações em que a transportadora devolveu opção. Prazo em dias (pior caso).",
        )
        tabela = pd.DataFrame(
            {
                "Transportadora": ranking["transportadora"],
                "Presença": ranking["presenca_pct"],
                "Preço médio": [fmt_brl(v) for v in ranking["preco_medio"]],
                "Prazo médio": [
                    f"{fmt_dec(v, 1)} dias" if pd.notna(v) else "—" for v in ranking["prazo_medio"]
                ],
                "Mais barata": ranking["mais_barata_pct"],
                "Mais rápida": ranking["mais_rapida_pct"],
            }
        )
        pct_coluna = st.column_config.ProgressColumn
        tema.mostrar_tabela(
            tabela,
            column_config={
                "Presença": pct_coluna("Presença", format="%.0f%%", min_value=0, max_value=100),
                "Mais barata": pct_coluna("Mais barata", format="%.0f%%", min_value=0, max_value=100),
                "Mais rápida": pct_coluna("Mais rápida", format="%.0f%%", min_value=0, max_value=100),
            },
        )
        st.caption(
            "A base identifica a transportadora apenas pelo código; por isso aparecem como “Transp. <código>”. "
            "Transportadoras com presença muito baixa foram ocultadas para evitar conclusões frágeis."
        )

    por_estado = analise["por_estado"]
    if not por_estado.empty:
        with st.container(key="card-estados"):
            tema.titulo_card(
                "Quem vence em cada estado",
                "Transportadora de menor preço médio e de menor prazo médio nos estados com mais cotações da loja.",
            )
            tabela_uf = pd.DataFrame(
                {
                    "Estado": por_estado["estado"],
                    "Cotações": por_estado["cotacoes"].map(fmt_int),
                    "Mais barata (preço médio)": [
                        f"{t} · {fmt_brl(p)}"
                        for t, p in zip(por_estado["mais_barata"], por_estado["preco_medio"])
                    ],
                    "Mais rápida (prazo médio)": [
                        f"{t} · {fmt_dec(p, 1)} dias" if t and pd.notna(p) else "—"
                        for t, p in zip(por_estado["mais_rapida"], por_estado["prazo_medio"])
                    ],
                    "Frete mais barato (médio)": [fmt_brl(v) for v in por_estado["frete_minimo_medio"]],
                }
            )
            tema.mostrar_tabela(tabela_uf)
            st.caption("Estados com pelo menos 30 cotações na amostra; por estado, só transportadoras com presença relevante.")

    # ---- Trade-off preço × prazo ----
    troca = analise["troca"]
    if troca and troca["custo_extra"] > 0.005:
        tema.destaque(
            f"<b>Quanto custa ganhar tempo?</b> Em média, escolher a opção mais rápida em vez da mais barata "
            f"custa <b>{fmt_brl(troca['custo_extra'])}</b> a mais por cotação e entrega "
            f"<b>{fmt_dec(troca['dias_ganhos'], 1)} dia(s)</b> antes "
            f"(prazo médio de {fmt_dec(troca['dias_barata'], 1)} para {fmt_dec(troca['dias_rapida'], 1)} dias).",
        )
    if analise["vantagem_media"]:
        tema.destaque(
            f"<b>Escolher bem compensa:</b> a opção mais barata custa, em média, "
            f"<b>{fmt_brl(analise['vantagem_media'])}</b> menos que a média das opções devolvidas em cada cotação."
        )


# ============================================================
# CONCLUSÃO
# ============================================================

tema.secao(
    "conclusao", "04", "O que os dados revelam",
    "O fio da história: volume na rede → cobertura da loja → escolha da transportadora.",
)

conclusoes = [
    f"Na rede, <b>{esc(lider['canal'])}</b> concentra <b>{fmt_pct(lider['pct'])}</b> das cotações de setembro.",
    f"Na loja {loja['loja']}, <b>{fmt_pct(pct_com_opcao, 1)}</b> das cotações voltaram com ao menos uma opção de frete"
    + (
        f"; <b>{fmt_int(sem_opcao_total)}</b> ficaram sem nenhuma."
        if sem_opcao_total
        else " — cobertura completa."
    ),
]
if not cob_visivel.empty:
    pior = cob_visivel.iloc[0]
    conclusoes.append(
        f"A maior lacuna de cobertura está em <b>{esc(pior['cidade'])}</b>: "
        f"<b>{fmt_int(pior['sem_opcao'])}</b> cotações sem opção ({fmt_pct(pior['pct_sem_opcao'])} da cidade)."
    )
if analise is not None:
    barata = analise["ranking"].sort_values("mais_barata_pct", ascending=False).iloc[0]
    rapida = analise["ranking"].sort_values("mais_rapida_pct", ascending=False).iloc[0]
    conclusoes.append(
        f"<b>{esc(barata['transportadora'])}</b> é a mais barata em <b>{fmt_pct(barata['mais_barata_pct'])}</b> das cotações; "
        f"<b>{esc(rapida['transportadora'])}</b> é a mais rápida em <b>{fmt_pct(rapida['mais_rapida_pct'])}</b>."
    )
    if barata["transportadora"] != rapida["transportadora"]:
        conclusoes.append(
            "A transportadora mais barata não é a mais rápida: a decisão de frete é um equilíbrio entre preço e prazo."
        )
tema.destaque("<ul>" + "".join(f"<li>{c}</li>" for c in conclusoes) + "</ul>")

tema.rodape()
