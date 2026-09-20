"""Gráficos Plotly no estilo Sisfrete (fundo transparente para assentar nos cartões)."""

import plotly.graph_objects as go

from tema import (
    ALERTA, BORDA, CARD, FUNDO, TEXTO, TEXTO_2, VERDE, VERDE_ESCURO, VERDE_MEDIO,
    fmt_compacto, fmt_int, fmt_pct,
)

ESCALA = [[0, VERDE_ESCURO], [0.5, VERDE_MEDIO], [1, VERDE]]


def _estilo(fig: go.Figure, altura: int, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXTO_2, size=13),
        margin=dict(l=8, r=28, t=10, b=8),
        showlegend=legenda,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(color=TEXTO)),
        hoverlabel=dict(bgcolor=CARD, bordercolor=VERDE, font=dict(color=TEXTO)),
    )
    fig.update_xaxes(gridcolor=BORDA, zerolinecolor=BORDA, linecolor=BORDA, automargin=True)
    fig.update_yaxes(gridcolor=BORDA, zerolinecolor=BORDA, linecolor=BORDA, automargin=True)
    return fig


def barras_horizontais(df, categoria: str, valor: str, textos, hover: str, altura: int, titulo_x: str):
    d = df.sort_values(valor, ascending=True)
    fig = go.Figure(
        go.Bar(
            x=d[valor],
            y=d[categoria],
            orientation="h",
            text=[textos(linha) for _, linha in d.iterrows()],
            textposition="outside",
            textfont=dict(color=TEXTO),
            cliponaxis=False,
            marker=dict(color=d[valor], colorscale=ESCALA, line=dict(width=0)),
            hovertemplate=hover,
        )
    )
    _estilo(fig, altura)
    fig.update_xaxes(title=titulo_x, range=[0, d[valor].max() * 1.25])
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return fig


def canais(df, altura: int = 330):
    d = df.assign(rotulo=lambda x: x["canal"])
    return barras_horizontais(
        d, "rotulo", "cotacoes",
        textos=lambda r: f"{fmt_compacto(r['cotacoes'])} · {fmt_pct(r['pct'])}",
        hover="<b>%{y}</b><br>%{x:,.0f} cotações<extra></extra>",
        altura=altura, titulo_x="Cotações em setembro",
    )


def cidades(df, altura: int = 520):
    return barras_horizontais(
        df, "cidade", "cotacoes",
        textos=lambda r: fmt_compacto(r["cotacoes"]),
        hover="<b>%{y}</b><br>%{x:,.0f} cotações<extra></extra>",
        altura=altura, titulo_x="Cotações em setembro",
    )


def janelas(df, altura: int = 330):
    """Barras por janela fixa de 7 dias; janela ainda em andamento aparece vazada."""
    rotulos = [
        f"{j}<br><span style='font-size:11px'>em andamento</span>" if p else j
        for j, p in zip(df["janela"], df["parcial"])
    ]
    fig = go.Figure(
        go.Bar(
            x=rotulos,
            y=df["cotacoes"],
            text=[fmt_compacto(v) for v in df["cotacoes"]],
            textposition="outside",
            textfont=dict(color=TEXTO),
            cliponaxis=False,
            marker=dict(
                color=["rgba(0,255,157,.18)" if p else VERDE for p in df["parcial"]],
                line=dict(color=VERDE, width=[1.5 if p else 0 for p in df["parcial"]]),
            ),
            customdata=list(zip(df["dias_com_dados"], df["media_dia"])),
            hovertemplate=(
                "<b>%{x}</b><br>%{y:,.0f} cotações<br>"
                "%{customdata[0]} dia(s) com dados · média de %{customdata[1]:,.0f}/dia<extra></extra>"
            ),
        )
    )
    _estilo(fig, altura)
    fig.update_yaxes(title="Cotações na janela", range=[0, max(df["cotacoes"].max() * 1.2, 1)])
    fig.update_xaxes(title="Janelas fixas de 7 dias", gridcolor="rgba(0,0,0,0)")
    return fig


def cobertura_por_cidade(df, altura: int = 420):
    """df já filtrado: cidades com mais cotações sem nenhuma opção de frete."""
    return barras_horizontais(
        df, "cidade", "sem_opcao",
        textos=lambda r: f"{fmt_int(r['sem_opcao'])} ({fmt_pct(r['pct_sem_opcao'])} da cidade)",
        hover="<b>%{y}</b><br>%{x:,.0f} cotações sem opção de frete<extra></extra>",
        altura=altura, titulo_x="Cotações sem nenhuma opção de frete",
    )


def vitorias_transportadoras(ranking, altura: int = 420):
    d = ranking.sort_values("mais_barata_pct", ascending=False).head(8).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(
        y=d["transportadora"], x=d["mais_barata_pct"], orientation="h", name="Mais barata",
        marker=dict(color=VERDE), text=[fmt_pct(v) for v in d["mais_barata_pct"]],
        textposition="outside", textfont=dict(color=TEXTO), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Foi a opção mais barata em %{x:.1f}% das cotações<extra></extra>",
    )
    fig.add_bar(
        y=d["transportadora"], x=d["mais_rapida_pct"], orientation="h", name="Mais rápida",
        marker=dict(color=ALERTA), text=[fmt_pct(v) for v in d["mais_rapida_pct"]],
        textposition="outside", textfont=dict(color=TEXTO), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Foi a opção mais rápida em %{x:.1f}% das cotações<extra></extra>",
    )
    _estilo(fig, altura, legenda=True)
    fig.update_layout(barmode="group", bargap=0.35)
    teto = max(d["mais_barata_pct"].max(), d["mais_rapida_pct"].max(), 1)
    fig.update_xaxes(title="% das cotações da loja", range=[0, teto * 1.25])
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return fig


def preco_x_prazo(ranking, altura: int = 420):
    d = ranking.dropna(subset=["prazo_medio"])
    fig = go.Figure()
    if d.empty:
        return _estilo(fig, altura)

    tamanho_ref = 2.0 * d["cotacoes"].max() / (46.0 ** 2)
    fig.add_trace(
        go.Scatter(
            x=d["prazo_medio"], y=d["preco_medio"], mode="markers+text",
            text=d["transportadora"], textposition="top center", textfont=dict(color=TEXTO, size=12),
            marker=dict(
                size=d["cotacoes"], sizemode="area", sizeref=tamanho_ref, sizemin=8,
                color=VERDE, opacity=0.78, line=dict(color=FUNDO, width=1.5),
            ),
            customdata=list(zip(d["cotacoes"], d["presenca_pct"])),
            hovertemplate=(
                "<b>%{text}</b><br>Preço médio: R$ %{y:,.2f}<br>Prazo médio: %{x:.1f} dias<br>"
                "Respondeu em %{customdata[0]:,} cotações (%{customdata[1]:.0f}%)<extra></extra>"
            ),
        )
    )
    if len(d) >= 3:
        fig.add_vline(x=d["prazo_medio"].median(), line=dict(color=BORDA, dash="dash"))
        fig.add_hline(y=d["preco_medio"].median(), line=dict(color=BORDA, dash="dash"))
    _estilo(fig, altura)
    fig.update_xaxes(title="Prazo médio de entrega (dias) →  mais lento")
    fig.update_yaxes(title="Preço médio (R$) →  mais caro")
    fig.add_annotation(
        xref="paper", yref="paper", x=0.01, y=0.02, showarrow=False, xanchor="left",
        text="canto inferior esquerdo = mais barata e mais rápida", font=dict(color=VERDE, size=12),
    )
    return fig

