"""Identidade visual (inspirada no site da Sisfrete), componentes HTML e formatação pt-BR."""

import html
import inspect

import streamlit as st

# ============================================================
# PALETA (extraída do material do hackathon / site da Sisfrete)
# ============================================================

VERDE = "#00ff9d"
VERDE_MEDIO = "#00b36e"
VERDE_ESCURO = "#093222"
FUNDO = "#04140e"
CARD = "#0b1b15"
BORDA = "#1c2b25"
TEXTO = "#f5f7f6"
TEXTO_2 = "#a8c9ba"
ALERTA = "#ffb547"

SITE_URL = "https://www.sisfrete.com.br"
LOGO_URL = f"{SITE_URL}/img/sisfrete-branco.png"
MARCA_URL = f"{SITE_URL}/img/sf.png"


# ============================================================
# FORMATAÇÃO (pt-BR)
# ============================================================

def fmt_int(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_dec(x, casas: int = 1) -> str:
    texto = f"{x:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_brl(x) -> str:
    return "R$ " + fmt_dec(x, 2)


def fmt_pct(x, casas: int = 0) -> str:
    return fmt_dec(x, casas) + "%"


def fmt_compacto(n) -> str:
    n = float(n)
    if n >= 1_000_000:
        return fmt_dec(n / 1_000_000, 1) + " mi"
    if n >= 10_000:
        return fmt_dec(n / 1_000, 0) + " mil"
    return fmt_int(n)


def esc(texto) -> str:
    return html.escape(str(texto), quote=True)


# ============================================================
# CSS
# ============================================================

def injetar_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --verde: {VERDE};
  --verde-medio: {VERDE_MEDIO};
  --verde-escuro: {VERDE_ESCURO};
  --fundo: {FUNDO};
  --card: {CARD};
  --borda: {BORDA};
  --texto: {TEXTO};
  --texto2: {TEXTO_2};
}}

.stApp {{
  background: var(--fundo);
  color: var(--texto);
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp li, .stApp label {{
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}

/* Remove o "chrome" padrão do Streamlit: o cabeçalho passa a ser o da Sisfrete */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stHeader"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{
  display: none !important;
}}

.block-container, [data-testid="stMainBlockContainer"] {{
  max-width: 1240px;
  padding: 6rem 2rem 3rem 2rem;
}}

/* ---------- Cabeçalho (nav) ---------- */
.sf-nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  height: 68px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 clamp(16px, 4vw, 48px);
  background: rgba(4, 20, 14, .88); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--borda);
}}
.sf-nav .sf-logo {{ display: flex; align-items: center; gap: 10px; }}
.sf-nav .sf-logo img {{ height: 30px; width: auto; }}
.sf-nav .sf-logo span {{ color: var(--texto2); font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; }}
.sf-nav .sf-links {{ display: flex; align-items: center; gap: 6px; }}
.sf-nav a.sf-link {{
  color: var(--texto2); text-decoration: none; font-size: .92rem; font-weight: 500;
  padding: 8px 12px; border-radius: 8px; transition: color .15s, background .15s;
}}
.sf-nav a.sf-link:hover {{ color: var(--verde); background: rgba(0, 255, 157, .07); }}
a.sf-btn {{
  background: var(--verde); color: #03130d !important; font-weight: 700; font-size: .8rem;
  letter-spacing: .04em; text-transform: uppercase; text-decoration: none;
  padding: 10px 18px; border-radius: 999px; margin-left: 8px; white-space: nowrap;
}}
a.sf-btn:hover {{ filter: brightness(1.08); }}
@media (max-width: 820px) {{ .sf-nav a.sf-link {{ display: none; }} .sf-nav .sf-logo span {{ display: none; }} }}

/* ---------- Hero ---------- */
.sf-hero {{
  position: relative; overflow: hidden;
  border: 1px solid var(--borda); border-radius: 22px;
  padding: clamp(24px, 4vw, 44px);
  background:
    radial-gradient(900px 320px at 92% -10%, rgba(0, 255, 157, .14), transparent 70%),
    linear-gradient(180deg, #0b1b15 0%, #04140e 100%);
}}
.sf-hero::after {{
  content: ""; position: absolute; right: -30px; bottom: -40px; width: 300px; height: 300px;
  background: url('{MARCA_URL}') no-repeat center / contain; opacity: .06; pointer-events: none;
}}
.sf-eyebrow {{ color: #6fd6a8; font-size: .74rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }}
.sf-hero h1 {{
  color: var(--texto) !important; font-size: clamp(2rem, 5vw, 3.4rem) !important; font-weight: 800 !important;
  line-height: 1.08 !important; letter-spacing: -.02em; margin: 10px 0 14px 0 !important; padding: 0 !important;
}}
.sf-hero h1 span {{ color: var(--verde); }}
.sf-hero p.sf-lead {{ color: var(--texto2); font-size: 1.08rem; line-height: 1.6; max-width: 780px; margin: 0 0 22px 0; }}

/* ---------- Cartões de indicadores ---------- */
.sf-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 6px 0 4px 0; }}
.sf-stat {{ background: rgba(11, 27, 21, .9); border: 1px solid var(--borda); border-radius: 14px; padding: 16px 18px; }}
.sf-stat-label {{ color: #7fa896; font-size: .68rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
.sf-stat-valor {{ color: var(--texto); font-size: 1.85rem; font-weight: 800; letter-spacing: -.02em; margin-top: 4px; }}
.sf-stat-det {{ color: var(--texto2); font-size: .82rem; margin-top: 2px; }}

/* ---------- Seções ---------- */
.sf-sec {{ margin: 46px 0 18px 0; padding-top: 12px; border-top: 1px solid var(--borda); }}
.sf-sec .sf-num {{ color: var(--verde); font-size: .95rem; font-weight: 700; letter-spacing: .1em; }}
.sf-sec h2 {{ color: var(--texto) !important; font-size: 1.85rem !important; font-weight: 800 !important; letter-spacing: -.02em; margin: 2px 0 6px 0 !important; padding: 0 !important; }}
.sf-sec p {{ color: var(--texto2); font-size: 1rem; line-height: 1.55; max-width: 820px; margin: 0; }}

/* ---------- Cartões de gráfico (containers com key="card-...") ---------- */
[class*="st-key-card-"] {{
  background: var(--card); border: 1px solid var(--borda); border-radius: 18px; padding: 20px 20px 10px 20px;
}}
.sf-card-titulo {{ color: var(--texto); font-size: 1.05rem; font-weight: 700; margin: 0 0 2px 0; }}
.sf-card-sub {{ color: var(--texto2); font-size: .86rem; line-height: 1.45; margin: 0 0 8px 0; }}

/* ---------- Destaques ("o que os dados mostram") ---------- */
.sf-insight {{
  background: linear-gradient(90deg, rgba(0, 255, 157, .09), rgba(0, 255, 157, .02));
  border: 1px solid rgba(0, 255, 157, .22); border-left: 4px solid var(--verde);
  border-radius: 12px; padding: 14px 18px; margin: 14px 0; color: var(--texto); font-size: .97rem; line-height: 1.55;
}}
.sf-insight b {{ color: var(--verde); font-weight: 700; }}
.sf-insight.sf-alerta {{ border-color: rgba(255, 181, 71, .3); border-left-color: {ALERTA};
  background: linear-gradient(90deg, rgba(255, 181, 71, .09), rgba(255, 181, 71, .02)); }}
.sf-insight.sf-alerta b {{ color: {ALERTA}; }}
.sf-insight ul {{ margin: 6px 0 0 0; padding-left: 20px; }}
.sf-insight li {{ margin: 4px 0; }}

/* ---------- Rodapé ---------- */
.sf-footer {{
  margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--borda);
  display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between;
  color: #7fa896; font-size: .82rem;
}}
.sf-footer img {{ height: 24px; width: auto; opacity: .9; }}
.sf-footer a {{ color: var(--texto2); text-decoration: none; margin-right: 14px; }}
.sf-footer a:hover {{ color: var(--verde); }}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# COMPONENTES
# ============================================================

def cabecalho() -> None:
    st.markdown(
        f'<div class="sf-nav">'
        f'<div class="sf-logo"><a href="{SITE_URL}" target="_blank" rel="noopener">'
        f'<img src="{LOGO_URL}" alt="SISFRETE"></a><span>Frete Estratégico</span></div>'
        f'<div class="sf-links">'
        f'<a class="sf-link" href="#rede">A rede</a>'
        f'<a class="sf-link" href="#loja">Uma loja</a>'
        f'<a class="sf-link" href="#transportadoras">Transportadoras</a>'
        f'<a class="sf-btn" href="{SITE_URL}" target="_blank" rel="noopener">Conheça a Sisfrete</a>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def hero(titulo_verde: str, texto: str, indicadores: list) -> None:
    cards = "".join(
        f'<div class="sf-stat"><div class="sf-stat-label">{esc(rotulo)}</div>'
        f'<div class="sf-stat-valor">{esc(valor)}</div>'
        + (f'<div class="sf-stat-det">{esc(det)}</div>' if det else "")
        + "</div>"
        for rotulo, valor, det in indicadores
    )
    st.markdown(
        f'<section class="sf-hero">'
        f'<div class="sf-eyebrow">Hackathon · Unimar Tech Summit 2026 · Marília · Grupo 08</div>'
        f'<h1>Frete Estratégico <span>{esc(titulo_verde)}</span></h1>'
        f'<p class="sf-lead">{esc(texto)}</p>'
        f'<div class="sf-stats">{cards}</div>'
        f'</section>',
        unsafe_allow_html=True,
    )


def indicadores(itens: list) -> None:
    cards = "".join(
        f'<div class="sf-stat"><div class="sf-stat-label">{esc(rotulo)}</div>'
        f'<div class="sf-stat-valor">{esc(valor)}</div>'
        + (f'<div class="sf-stat-det">{esc(det)}</div>' if det else "")
        + "</div>"
        for rotulo, valor, det in itens
    )
    st.markdown(f'<div class="sf-stats">{cards}</div>', unsafe_allow_html=True)


def secao(ancora: str, numero: str, titulo: str, texto: str) -> None:
    st.markdown(
        f'<div class="sf-sec" id="{esc(ancora)}"><span class="sf-num">{esc(numero)}</span>'
        f'<h2>{esc(titulo)}</h2><p>{esc(texto)}</p></div>',
        unsafe_allow_html=True,
    )


def titulo_card(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<div class="sf-card-titulo">{esc(titulo)}</div>'
        + (f'<div class="sf-card-sub">{esc(subtitulo)}</div>' if subtitulo else ""),
        unsafe_allow_html=True,
    )


def destaque(html_interno: str, alerta: bool = False) -> None:
    """`html_interno` deve vir com valores dinâmicos já escapados (use esc())."""
    classe = "sf-insight sf-alerta" if alerta else "sf-insight"
    st.markdown(f'<div class="{classe}">{html_interno}</div>', unsafe_allow_html=True)


def rodape() -> None:
    st.markdown(
        f'<div class="sf-footer"><div><img src="{LOGO_URL}" alt="SISFRETE"></div>'
        f'<div>Dados cedidos pela Sisfrete para uso exclusivo no Hackathon Unimar Tech Summit 2026. '
        f'Não republique nem use fora do evento.</div>'
        f'<div><a href="{SITE_URL}/cotacao-de-frete-automatizado" target="_blank" rel="noopener">Cotação de frete</a>'
        f'<a href="{SITE_URL}/torre-de-controle" target="_blank" rel="noopener">Torre de controle</a>'
        f'<a href="{SITE_URL}/sobre-nos" target="_blank" rel="noopener">Sobre nós</a></div>'
        f'<div style="width:100%">Copyright © 2026 Sisfrete · Projeto do Grupo 08</div></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# EXIBIÇÃO (compatível com versões novas e antigas do Streamlit)
# ============================================================

def _largura_total(func) -> dict:
    """Streamlit novo usa width='stretch'; o antigo usa use_container_width=True."""
    param = inspect.signature(func).parameters.get("width")
    if param is not None and param.default == "stretch":
        return {"width": "stretch"}
    return {"use_container_width": True}


def mostrar_grafico(fig) -> None:
    st.plotly_chart(fig, config={"displayModeBar": False}, **_largura_total(st.plotly_chart))


def mostrar_tabela(df, **kwargs) -> None:
    st.dataframe(df, hide_index=True, **_largura_total(st.dataframe), **kwargs)
