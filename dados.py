"""Acesso à API OpenSearch da Sisfrete e preparação dos dados.

Regras do hackathon respeitadas aqui:
  * só índices de setembro de 2026 (quotations-*-2026.09);
  * eixo de tempo sempre em janelas fixas de 7 dias (cortes explícitos);
  * agregações no servidor sempre que possível; o que depende de correlacionar
    campos dentro de nf.cotacoes (array NÃO-nested) é feito em código Python.
"""

import os
import re
import time
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.opensearch.sisfrete.com.br"
USUARIO = os.getenv("SISFRETE_USUARIO")
SENHA = os.getenv("SISFRETE_SENHA")

INDICES_SETEMBRO = "quotations-*-2026.09"
JANELA_DIAS = 7
INICIO_MES = date(2026, 9, 1)
FIM_MES = date(2026, 10, 1)  # exclusivo
FUSO = "-03:00"  # @timestamp está em UTC; os cortes usam o horário de Brasília

FILTRO_SETEMBRO = {
    "range": {"@timestamp": {"gte": "2026-09-01", "lt": "2026-10-01", "time_zone": FUSO}}
}
# Cotação que devolveu pelo menos uma opção de frete válida (total > 0)
TEM_OPCAO = {"range": {"nf.cotacoes.total": {"gt": 0}}}

_REGEX_INDICE = re.compile(r"^quotations-(\d+)-2026\.09$")
_sessao = requests.Session()


# ============================================================
# CLIENTE HTTP
# ============================================================

class ErroAPI(Exception):
    def __init__(self, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.status = status


def credenciais_ok() -> bool:
    return bool(USUARIO and SENHA)


def _requisitar(metodo: str, caminho: str, *, params=None, corpo=None, timeout: int = 120):
    """Chamada HTTP com repetição em 429/5xx (a API é compartilhada com clientes reais)."""
    for tentativa in range(3):
        try:
            resposta = _sessao.request(
                metodo,
                f"{API_URL}{caminho}",
                auth=(USUARIO, SENHA),
                params=params,
                json=corpo,
                timeout=timeout,
            )
        except requests.RequestException as erro:
            raise ErroAPI(
                "Não foi possível conectar à API da Sisfrete. "
                "Verifique a conexão e tente novamente."
            ) from erro

        if resposta.status_code in (429, 502, 503, 504) and tentativa < 2:
            time.sleep(2 * (tentativa + 1))
            continue

        if resposta.status_code == 401:
            raise ErroAPI("Usuário ou senha incorretos (401). Confira o arquivo .env.", 401)
        if resposta.status_code == 403:
            raise ErroAPI("Acesso negado pela API (403): consulta fora do permitido.", 403)
        if resposta.status_code == 404:
            raise ErroAPI("Índice não encontrado (404).", 404)
        if resposta.status_code == 400:
            raise ErroAPI("Consulta recusada pela API (400).", 400)
        if resposta.status_code == 429:
            raise ErroAPI("A API está sob carga (429). Aguarde alguns segundos e recarregue.", 429)
        if not resposta.ok:
            raise ErroAPI(f"A API respondeu com erro {resposta.status_code}.", resposta.status_code)

        return resposta.json()

    raise ErroAPI("A API não respondeu a tempo. Tente novamente em instantes.")


def _buscar_com_fallback(caminho: str, montar_corpo):
    """Tenta os campos keyword como estão no mapping e, se der 400, com o sufixo .keyword."""
    ultimo = None
    for sufixo in ("", ".keyword"):
        try:
            return _requisitar("POST", caminho, corpo=montar_corpo(sufixo))
        except ErroAPI as erro:
            if erro.status != 400:
                raise
            ultimo = erro
    raise ultimo


def _total(resposta: dict) -> int:
    total = resposta.get("hits", {}).get("total", 0)
    return int(total.get("value", 0) if isinstance(total, dict) else total or 0)


# ============================================================
# LOJAS (CLIENTES)
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def listar_lojas() -> pd.DataFrame:
    """Uma linha por loja com cotações em setembro. O ID vem do nome do índice
    (quotations-<id_cliente>-2026.09), que é o mesmo valor de nf.cliente."""
    itens = _requisitar(
        "GET", "/_cat/indices/quotations-*", params={"format": "json", "h": "index,docs.count"}
    )
    linhas = []
    for item in itens:
        casou = _REGEX_INDICE.match(item.get("index", ""))
        if not casou:
            continue
        try:
            docs = int(item.get("docs.count") or 0)
        except (TypeError, ValueError):
            docs = 0
        linhas.append({"loja": int(casou.group(1)), "cotacoes": docs})

    df = pd.DataFrame(linhas, columns=["loja", "cotacoes"])
    return df.sort_values("cotacoes", ascending=False).reset_index(drop=True)


# ============================================================
# PEÇAS REUTILIZÁVEIS
# ============================================================

def _agg_por_dia() -> dict:
    return {
        "date_histogram": {
            "field": "@timestamp",
            "calendar_interval": "day",
            "time_zone": FUSO,
            "format": "yyyy-MM-dd",
            "min_doc_count": 0,
        }
    }


def _df_dias(buckets: list) -> pd.DataFrame:
    linhas = [
        {"data": date.fromisoformat(b["key_as_string"][:10]), "cotacoes": int(b["doc_count"])}
        for b in buckets
    ]
    return pd.DataFrame(linhas, columns=["data", "cotacoes"])


def agrupar_em_janelas(df_dias: pd.DataFrame, dias: int = JANELA_DIAS) -> pd.DataFrame:
    """Agrupa os totais diários em janelas FIXAS de `dias` dias a partir de 01/09.

    (Um date_histogram de 7d no servidor alinha as janelas à época Unix, ou seja,
    começaria numa quinta-feira de agosto. Fazendo aqui o corte é explícito.)
    """
    colunas = ["janela", "inicio", "fim", "cotacoes", "dias_com_dados", "media_dia", "parcial"]
    if df_dias.empty:
        return pd.DataFrame(columns=colunas)

    por_dia = dict(zip(df_dias["data"], df_dias["cotacoes"]))
    ultimo_dia = df_dias["data"].max()
    linhas = []
    inicio = INICIO_MES
    while inicio <= ultimo_dia and inicio < FIM_MES:
        fim = min(inicio + timedelta(days=dias - 1), FIM_MES - timedelta(days=1))
        ate = min(fim, ultimo_dia)
        dias_com_dados = (ate - inicio).days + 1
        total = sum(por_dia.get(inicio + timedelta(days=i), 0) for i in range(dias_com_dados))
        linhas.append(
            {
                "janela": f"{inicio:%d/%m} – {fim:%d/%m}",
                "inicio": inicio,
                "fim": fim,
                "cotacoes": total,
                "dias_com_dados": dias_com_dados,
                "media_dia": total / dias_com_dados,
                "parcial": ultimo_dia < fim,  # a janela ainda está recebendo dados
            }
        )
        inicio = fim + timedelta(days=1)
    return pd.DataFrame(linhas, columns=colunas)


def _df_canais(buckets: list) -> pd.DataFrame:
    df = pd.DataFrame(
        [{"canal": b["key"], "cotacoes": int(b["doc_count"])} for b in buckets],
        columns=["canal", "cotacoes"],
    )
    total = df["cotacoes"].sum()
    df["pct"] = df["cotacoes"] / total * 100 if total else 0.0
    return df


def _rotulo_cidade(bucket: dict) -> str:
    ufs = bucket.get("uf", {}).get("buckets", [])
    return f"{bucket['key']}/{ufs[0]['key']}" if ufs else str(bucket["key"])


# ============================================================
# VISÃO GERAL DA REDE
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def resumo_mercado() -> dict:
    """Canais, evolução diária e top 15 cidades — tudo numa única consulta agregada."""

    def corpo(sufixo: str) -> dict:
        return {
            "size": 0,
            "track_total_hits": True,
            "query": FILTRO_SETEMBRO,
            "aggs": {
                "canais": {"terms": {"field": f"nf.canal_web{sufixo}", "size": 10}},
                "por_dia": _agg_por_dia(),
                "cidades": {
                    "terms": {"field": f"nf.nome_cidade{sufixo}", "size": 15},
                    "aggs": {"uf": {"terms": {"field": f"nf.estado{sufixo}", "size": 1}}},
                },
            },
        }

    resposta = _buscar_com_fallback(f"/{INDICES_SETEMBRO}/_search", corpo)
    aggs = resposta.get("aggregations", {})

    dias = _df_dias(aggs.get("por_dia", {}).get("buckets", []))
    cidades = pd.DataFrame(
        [
            {"cidade": _rotulo_cidade(b), "cotacoes": int(b["doc_count"])}
            for b in aggs.get("cidades", {}).get("buckets", [])
        ],
        columns=["cidade", "cotacoes"],
    )
    return {
        "total": _total(resposta),
        "canais": _df_canais(aggs.get("canais", {}).get("buckets", [])),
        "dias": dias,
        "janelas": agrupar_em_janelas(dias),
        "cidades": cidades,
    }


# ============================================================
# UMA LOJA
# ============================================================

_CAMPOS_AMOSTRA = [
    "@timestamp",
    "nf.canal_web",
    "nf.nome_cidade",
    "nf.estado",
    "nf.cotacoes.transportadora",
    "nf.cotacoes.frete",
    "nf.cotacoes.pedagio",
    "nf.cotacoes.gris",
    "nf.cotacoes.total",
    "nf.cotacoes.p_min",
    "nf.cotacoes.p_max",
]


def explodir_cotacoes(hits: list) -> pd.DataFrame:
    """Uma linha por (cotação, transportadora). É aqui que se correlaciona preço, prazo e
    região de forma segura: cada linha vem do MESMO objeto dentro do array nf.cotacoes."""
    linhas = []
    for hit in hits:
        nf = (hit.get("_source") or {}).get("nf") or {}
        cotacoes = nf.get("cotacoes") or []
        if isinstance(cotacoes, dict):
            cotacoes = [cotacoes]
        for c in cotacoes:
            if not isinstance(c, dict):
                continue
            linhas.append(
                {
                    "doc": hit.get("_id"),
                    "estado": nf.get("estado") or None,
                    "cidade": nf.get("nome_cidade") or None,
                    "transportadora": c.get("transportadora"),
                    "frete": c.get("frete"),
                    "pedagio": c.get("pedagio"),
                    "gris": c.get("gris"),
                    "total": c.get("total"),
                    "p_min": c.get("p_min"),
                    "p_max": c.get("p_max"),
                }
            )
    return preparar_opcoes(pd.DataFrame(linhas))


def preparar_opcoes(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["doc", "estado", "cidade", "transportadora", "frete", "pedagio", "gris",
               "total", "p_min", "p_max", "prazo"]
    if df.empty:
        return pd.DataFrame(columns=colunas)

    df = df.copy()
    for coluna in ["transportadora", "frete", "pedagio", "gris", "total", "p_min", "p_max"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    # Muitos campos vêm vazios (0/""/false): só vale opção com transportadora e total > 0
    df = df.dropna(subset=["transportadora"])
    df = df[df["total"] > 0].copy()
    if df.empty:
        return pd.DataFrame(columns=colunas)

    # Prazo em dias: p_max (pior caso); se vier zerado, usa p_min
    df["prazo"] = df["p_max"].where(df["p_max"] > 0, df["p_min"].where(df["p_min"] > 0))
    df["transportadora"] = "Transp. " + df["transportadora"].astype(int).astype(str)
    return df[colunas].reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner=False)
def analisar_loja(loja_id: int, tamanho_amostra: int = 5000) -> dict:
    indice = f"quotations-{int(loja_id)}-2026.09"

    def corpo_agregado(sufixo: str) -> dict:
        return {
            "size": 0,
            "track_total_hits": True,
            "query": FILTRO_SETEMBRO,
            "aggs": {
                "canais": {"terms": {"field": f"nf.canal_web{sufixo}", "size": 10}},
                "por_dia": _agg_por_dia(),
                "com_opcao": {"filter": TEM_OPCAO},
                "cidades": {
                    "terms": {"field": f"nf.nome_cidade{sufixo}", "size": 500},
                    "aggs": {
                        "sem_opcao": {"filter": {"bool": {"must_not": [TEM_OPCAO]}}},
                        "uf": {"terms": {"field": f"nf.estado{sufixo}", "size": 1}},
                    },
                },
            },
        }

    agregado = _buscar_com_fallback(f"/{indice}/_search", corpo_agregado)
    aggs = agregado.get("aggregations", {})
    total = _total(agregado)

    dias = _df_dias(aggs.get("por_dia", {}).get("buckets", []))
    cidades = pd.DataFrame(
        [
            {
                "cidade": _rotulo_cidade(b),
                "cotacoes": int(b["doc_count"]),
                "sem_opcao": int(b.get("sem_opcao", {}).get("doc_count", 0)),
            }
            for b in aggs.get("cidades", {}).get("buckets", [])
        ],
        columns=["cidade", "cotacoes", "sem_opcao"],
    )
    cidades["pct_sem_opcao"] = (
        cidades["sem_opcao"] / cidades["cotacoes"] * 100 if len(cidades) else pd.Series(dtype=float)
    )

    # Amostra (mais recentes) para cruzar transportadora × preço × prazo × estado em código
    amostra = _requisitar(
        "POST",
        f"/{indice}/_search",
        corpo={
            "size": int(tamanho_amostra),
            "track_total_hits": False,
            "query": FILTRO_SETEMBRO,
            "sort": [{"@timestamp": "desc"}],
            "_source": _CAMPOS_AMOSTRA,
        },
    )
    hits = amostra.get("hits", {}).get("hits", [])

    return {
        "loja": int(loja_id),
        "total": total,
        "com_opcao": int(aggs.get("com_opcao", {}).get("doc_count", 0)),
        "canais": _df_canais(aggs.get("canais", {}).get("buckets", [])),
        "dias": dias,
        "janelas": agrupar_em_janelas(dias),
        "cidades": cidades,
        "docs_amostra": len(hits),
        "opcoes": explodir_cotacoes(hits),
    }


# ============================================================
# TRANSPORTADORAS: preço × prazo × região
# ============================================================

def analisar_transportadoras(opcoes: pd.DataFrame) -> dict | None:
    """Tudo calculado por cotação (doc), nunca por agregação ingênua do array."""
    if opcoes.empty:
        return None

    op = opcoes.copy()
    n_docs = op["doc"].nunique()

    menor_preco = op.groupby("doc")["total"].transform("min")
    menor_prazo = op.groupby("doc")["prazo"].transform("min")
    op["mais_barata"] = op["total"] <= menor_preco + 1e-9
    op["mais_rapida"] = op["prazo"].notna() & (op["prazo"] <= menor_prazo + 1e-9)

    g = op.groupby("transportadora")
    ranking = pd.DataFrame(
        {
            "cotacoes": g["doc"].nunique(),
            "preco_medio": g["total"].mean(),
            "prazo_medio": g["prazo"].mean(),
            "n_mais_barata": op[op["mais_barata"]].groupby("transportadora")["doc"].nunique(),
            "n_mais_rapida": op[op["mais_rapida"]].groupby("transportadora")["doc"].nunique(),
        }
    ).fillna({"n_mais_barata": 0, "n_mais_rapida": 0})
    ranking["presenca_pct"] = ranking["cotacoes"] / n_docs * 100
    ranking["mais_barata_pct"] = ranking["n_mais_barata"] / n_docs * 100
    ranking["mais_rapida_pct"] = ranking["n_mais_rapida"] / n_docs * 100

    # Esconde transportadoras com presença insignificante (ruído estatístico)
    minimo = max(10, int(0.01 * n_docs))
    visiveis = ranking[ranking["cotacoes"] >= minimo]
    ranking = (visiveis if not visiveis.empty else ranking).reset_index()
    ranking = ranking.sort_values(["mais_barata_pct", "presenca_pct"], ascending=False).reset_index(drop=True)

    # --- custo de escolher a mais rápida em vez da mais barata (por cotação) ---
    com_prazo = op.dropna(subset=["prazo"])
    varias = com_prazo.groupby("doc")["total"].transform("size") >= 2
    com_prazo = com_prazo[varias]
    troca = None
    if not com_prazo.empty:
        barata = com_prazo.sort_values(["doc", "total", "prazo"]).groupby("doc").first()
        rapida = com_prazo.sort_values(["doc", "prazo", "total"]).groupby("doc").first()
        troca = {
            "cotacoes": int(len(barata)),
            "custo_extra": float((rapida["total"] - barata["total"]).mean()),
            "dias_ganhos": float((barata["prazo"] - rapida["prazo"]).mean()),
            "dias_barata": float(barata["prazo"].mean()),
            "dias_rapida": float(rapida["prazo"].mean()),
        }

    # --- vantagem média de escolher a mais barata frente à média das opções ---
    varias_opcoes = op.groupby("doc")["total"].transform("size") >= 2
    multi = op[varias_opcoes].groupby("doc")["total"].agg(["mean", "min"])
    vantagem = float((multi["mean"] - multi["min"]).mean()) if not multi.empty else None

    # --- região: melhor transportadora por estado ---
    linhas = []
    com_estado = op.dropna(subset=["estado"])
    for uf, d in com_estado.groupby("estado"):
        n = d["doc"].nunique()
        if n < 30:
            continue
        por_t = d.groupby("transportadora").agg(
            preco=("total", "mean"), prazo=("prazo", "mean"), n=("doc", "nunique")
        )
        por_t = por_t[por_t["n"] >= max(5, int(0.05 * n))]
        if por_t.empty:
            continue
        barata_uf = por_t["preco"].idxmin()
        rapida_uf = por_t["prazo"].idxmin() if por_t["prazo"].notna().any() else None
        linhas.append(
            {
                "estado": uf,
                "cotacoes": n,
                "mais_barata": barata_uf,
                "preco_medio": float(por_t.loc[barata_uf, "preco"]),
                "mais_rapida": rapida_uf,
                "prazo_medio": float(por_t.loc[rapida_uf, "prazo"]) if rapida_uf else None,
                "frete_minimo_medio": float(d.groupby("doc")["total"].min().mean()),
            }
        )
    por_estado = (
        pd.DataFrame(linhas).sort_values("cotacoes", ascending=False).head(15).reset_index(drop=True)
        if linhas
        else pd.DataFrame()
    )

    return {
        "docs_com_opcao": int(n_docs),
        "n_transportadoras": int(op["transportadora"].nunique()),
        "frete_minimo_medio": float(op.groupby("doc")["total"].min().mean()),
        "prazo_medio_barata": troca["dias_barata"] if troca else None,
        "vantagem_media": vantagem,
        "troca": troca,
        "ranking": ranking,
        "por_estado": por_estado,
    }
