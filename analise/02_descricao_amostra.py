"""
Etapa 2 - Descrição da amostra
Uso:  python analise/02_descricao_amostra.py   (requer a base gerada por 01_limpeza.py)
Gera:
  analise/resultados/02_amostra_tabelas.xlsx
  analise/resultados/figuras/02_*.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent
d = pd.read_excel(RAIZ / "dados" / "base_limpa.xlsx", sheet_name="dados")
OUT = RAIZ / "resultados"
FIG = OUT / "figuras"
FIG.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- estilo
COR = {"Docente": "#2a78d6", "Estudante": "#eb6834"}   # slots 1 e 2 da paleta validada
UNICA = "#2a78d6"
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "axes.edgecolor": BASE, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": INK2, "figure.facecolor": SURF,
    "axes.facecolor": SURF, "savefig.facecolor": SURF, "savefig.dpi": 200,
})

def limpa_eixos(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)

def rot_pct(v):
    return "<1%" if 0 < v < 1 else f"{v:.0f}%"

def salvar(fig, nome, fonte):
    fig.text(0.01, 0.01, fonte, color=MUTED, fontsize=8, ha="left", va="bottom")
    fig.savefig(FIG / nome, bbox_inches="tight")
    plt.close(fig)

FONTE = "Fonte: Pesquisa Percepções e usos da IA na FURB (PIBIC 168/2025)."

# ---------------------------------------------------------------- tabelas
def freq(serie, ordem=None, nome=None):
    t = serie.value_counts(dropna=False)
    if ordem:
        t = t.reindex([o for o in ordem if o in t.index] +
                      [i for i in t.index if i not in ordem])
    df = pd.DataFrame({"n": t, "%": (100 * t / t.sum()).round(1)})
    df.index.name = nome or serie.name
    return df

def cruzada(var, ordem=None):
    n = pd.crosstab(d[var], d["grupo"], margins=True, margins_name="Total")
    if ordem:
        n = n.reindex([o for o in ordem if o in n.index] + ["Total"])
    pct = (100 * n / n.loc["Total"]).round(1)
    out = pd.concat({"n": n, "% na coluna": pct}, axis=1)
    out.index.name = var
    return out

FAIXAS = ["Menos de 20 anos", "Entre 20 e 29 anos", "Entre 30 e 49 anos",
          "Entre 50 e 59 anos", "Mais de 59 anos"]
GENEROS = ["Feminino", "Masculino", "Outro / não binário"]
est, doc = d[d.grupo == "Estudante"], d[d.grupo == "Docente"]

tabs = {
    "T1_grupo": freq(d["grupo"], ["Estudante", "Docente"]),
    "T2_genero_x_grupo": cruzada("genero", GENEROS),
    "T3_faixa_x_grupo": cruzada("faixa_etaria", FAIXAS),
    "T4_est_nivel": freq(est["est_nivel"], ["Graduação", "Especialização", "Mestrado",
                                             "Doutorado", "Aluno especial"]),
    "T5_est_curso": freq(est["est_curso"]),
    "T6_doc_departamento": freq(doc["doc_departamento"]),
    "T7_doc_vinculo": freq(doc["doc_vinculo"]),
}
ativ = {"Docência na graduação": "doc_ativ_graduacao", "Pesquisa": "doc_ativ_pesquisa",
        "Cargos de gestão e/ou chefia": "doc_ativ_gestao", "Extensão": "doc_ativ_extensao",
        "Docência na pós-graduação": "doc_ativ_pos", "Outra": "doc_ativ_outra"}
t8 = pd.DataFrame({"n": [int(doc[v].sum()) for v in ativ.values()]}, index=list(ativ))
t8["% dos docentes"] = (100 * t8["n"] / len(doc)).round(1)
t8.index.name = "Atividade (múltipla escolha)"
n_ativ = doc[[v for v in ativ.values()]].sum(axis=1)
t8 = t8.astype(float)
t8.loc["Média de atividades por docente", "n"] = round(n_ativ.mean(), 2)
tabs["T8_doc_atividades"] = t8

mes = d["inicio"].dt.to_period("M").astype(str)
tabs["T9_coleta_mes"] = pd.crosstab(mes, d["grupo"], margins=True, margins_name="Total")
tabs["T9_coleta_mes"].index.name = "mês de início"
dur = d.groupby("grupo")["duracao_min"].describe(percentiles=[.25, .5, .75]).round(1)
dur.loc["Total"] = d["duracao_min"].describe(percentiles=[.25, .5, .75]).round(1)
tabs["T10_duracao_min"] = dur

with pd.ExcelWriter(OUT / "02_amostra_tabelas.xlsx", engine="openpyxl") as xw:
    for nome, t in tabs.items():
        t.to_excel(xw, sheet_name=nome[:31])

# ---------------------------------------------------------------- figuras
def barras_grupo(var, ordem, titulo, nome):
    pct = pd.crosstab(d[var], d["grupo"], normalize="columns").reindex(ordem).fillna(0) * 100
    n = pd.crosstab(d[var], d["grupo"]).reindex(ordem).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(7, 0.55 * len(ordem) + 1.4))
    h = 0.36
    y = range(len(ordem))
    for k, g in enumerate(["Docente", "Estudante"]):
        pos = [i + (k - 0.5) * (h + 0.03) for i in y]
        ax.barh(pos, pct[g], height=h, color=COR[g],
                label=f"{g}s (n={int((d.grupo == g).sum())})")
        for p, v, nn in zip(pos, pct[g], n[g]):
            ax.text(v + 0.8, p, f"{rot_pct(v)} ({nn})", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(list(y), ordem)
    ax.invert_yaxis()
    ax.set_xlim(0, max(pct.max().max() * 1.22, 10))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title(titulo)
    ax.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=INK2)
    limpa_eixos(ax)
    salvar(fig, nome, FONTE + " % dentro de cada grupo.")

barras_grupo("genero", GENEROS, "Gênero, por grupo", "02_genero_grupo.png")
barras_grupo("faixa_etaria", FAIXAS, "Faixa etária, por grupo", "02_faixa_grupo.png")

def barras_simples(serie_n, total, titulo, nome, nota):
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(serie_n) + 1.3))
    pct = 100 * serie_n / total
    ax.barh(range(len(serie_n)), pct, height=0.6, color=UNICA)
    for i, (v, nn) in enumerate(zip(pct, serie_n)):
        ax.text(v + 0.8, i, f"{rot_pct(v)} ({nn})", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(serie_n)), serie_n.index)
    ax.invert_yaxis()
    ax.set_xlim(0, pct.max() * 1.2)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title(titulo)
    limpa_eixos(ax)
    salvar(fig, nome, FONTE + " " + nota)

barras_simples(tabs["T4_est_nivel"]["n"], len(est),
               f"Estudantes por nível de curso (n={len(est)})", "02_est_nivel.png", "")
barras_simples(tabs["T7_doc_vinculo"]["n"], len(doc),
               f"Docentes por tipo de vínculo (n={len(doc)})", "02_doc_vinculo.png", "")
t8s = t8.drop("Média de atividades por docente")["n"].astype(int)
barras_simples(t8s, len(doc), f"Atividades dos docentes na FURB (n={len(doc)})",
               "02_doc_atividades.png", "Múltipla escolha; % dos docentes.")

# coleta acumulada
fig, ax = plt.subplots(figsize=(7, 3.2))
for g in ["Estudante", "Docente"]:
    s = d.loc[d.grupo == g, "inicio"].sort_values()
    ax.step(s, range(1, len(s) + 1), where="post", color=COR[g], linewidth=2)
    ax.text(s.iloc[-1], len(s), f"  {g}s ({len(s)})", va="center", fontsize=9, color=INK2)
ax.set_title("Respostas acumuladas ao longo da coleta")
ax.set_ylabel("respostas")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.yaxis.grid(True, color=GRID, linewidth=0.6)
ax.tick_params(axis="x", colors=MUTED)
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
salvar(fig, "02_coleta_acumulada.png", FONTE)

# ---------------------------------------------------------------- console
for nome, t in tabs.items():
    if nome in ("T5_est_curso", "T6_doc_departamento"):
        print(f"\n== {nome}: {len(t)} categorias; maiores:\n{t.head(5).to_string()}")
    else:
        print(f"\n== {nome}\n{t.to_string()}")
