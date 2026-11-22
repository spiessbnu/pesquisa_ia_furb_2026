"""
Etapa 4 - Análise descritiva por eixo (conhecimento, usos, percepções, futuro)
Uso:  python analise/04_descritiva.py   (requer base_indices gerada por 03_indices.py)
Gera:
  analise/resultados/04_descritiva_tabelas.xlsx
  analise/resultados/figuras/04_*.png

Percentuais sempre dentro do grupo (Docentes / Estudantes / Total).
Q17-Q23 foram respondidas apenas por usuários de IA (n=385); as tabelas dessas
questões usam essa base. "Não sei responder" aparece como categoria nas tabelas
e em cinza nos gráficos.
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
RAIZ = Path(__file__).resolve().parent
d = pd.read_excel(RAIZ / "dados" / "base_indices.xlsx", sheet_name="dados")
OUT = RAIZ / "resultados"
FIG = OUT / "figuras"
FIG.mkdir(parents=True, exist_ok=True)
GRUPOS = ["Docente", "Estudante"]
NG = {g: int((d.grupo == g).sum()) for g in GRUPOS}
usu = d[d.usuario_ia == 1]
NU = {g: int((usu.grupo == g).sum()) for g in GRUPOS}

# ------------------------------------------------------------------ estilo (paleta validada)
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COR = {"Docente": "#2a78d6", "Estudante": "#eb6834"}
SEQ5 = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]       # ordinal, claro -> escuro
SEQ4 = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
DIV5 = ["#e34948", "#f0a09f", "#d6d5cf", "#86b6ef", "#2a78d6"]       # neg ... nulo ... pos
NSR = "#ecebe6"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "axes.edgecolor": BASE, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": INK2, "figure.facecolor": SURF,
    "axes.facecolor": SURF, "savefig.facecolor": SURF, "savefig.dpi": 200,
})
FONTE = "Fonte: Pesquisa Percepções e usos da IA na FURB (PIBIC 168/2025)."

def lum(hexcor):
    r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def salvar(fig, nome, nota=""):
    # nota de rodapé abaixo de tudo (eixos, rótulos e legendas)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    y0 = min(inv.transform((0, a.get_tightbbox(r).y0))[1] for a in fig.axes)
    for lg in fig.legends:
        y0 = min(y0, inv.transform((0, lg.get_window_extent(r).y0))[1])
    fig.text(0.01, y0 - 0.02, (FONTE + " " + nota).strip(), color=MUTED, fontsize=8,
             ha="left", va="top")
    fig.savefig(FIG / nome, bbox_inches="tight")
    plt.close(fig)

def eixo_limpo(ax, grade="x"):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    if grade:
        getattr(ax, f"{grade}axis").grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)

# ------------------------------------------------------------------ rótulos das escalas
R = {
    "q11": {1: "Discordo totalmente", 2: "Discordo parcialmente", 3: "Neutro",
            4: "Concordo parcialmente", 5: "Concordo totalmente"},
    "dom": {0: "Nenhum", 1: "Baixo", 2: "Médio", 3: "Alto", 4: "Profissional"},
    "q15": {0: "Desconhece", 1: "Básico", 2: "Intermediário", 3: "Avançado", 4: "Muito avançado"},
    "q16": {0: "Nunca utiliza", 1: "Algumas vezes por semestre", 2: "Algumas vezes por mês",
            3: "Algumas vezes por semana", 4: "Diariamente"},
    "q17": {1: "Menos de 1 ano", 2: "1 a 2 anos", 3: "2 a 3 anos", 4: "Mais de 3 anos"},
    "freq": {0: "Nunca", 1: "Raramente", 2: "Eventualmente", 3: "Frequentemente",
             4: "Muito frequentemente"},
    "q22": {0: "Insignificantes", 1: "Pouco importantes", 2: "Moderadamente importantes",
            3: "Muito importantes", 4: "Indispensáveis"},
    "q24": {0: "Nenhuma", 1: "Baixa", 2: "Moderada", 3: "Alta", 4: "Altíssima"},
    "q25": {-2: "Muito negativo", -1: "Relativamente negativo", 0: "Nulo",
            1: "Relativamente positivo", 2: "Muito positivo"},
    "q26": {1: "Imediatamente", 2: "Curto prazo", 3: "Médio prazo", 4: "Longo prazo", 5: "Nunca"},
}
Q23_ORD = ["Ampliar", "Formas diferentes", "Manter", "Usar menos", "Parar"]

ITENS = {
    "Q11": ("q11", {"q11_conhecimento": "Tenho alto grau de conhecimento",
                    "q11_acompanha": "Acompanho as novidades tecnológicas",
                    "q11_facilidade": "Tenho facilidade em aprender",
                    "q11_pouco_interesse": "Tenho pouco interesse nas novidades"}),
    "Q13": ("dom", {"q13_webdesign": "Web design", "q13_programacao": "Linguagens de programação",
                    "q13_bancodados": "Bancos de dados e SQL", "q13_nuvem": "Computação em nuvem"}),
    "Q14": ("dom", {"q14_ia": "Inteligência Artificial", "q14_iot": "Internet das Coisas",
                    "q14_blockchain": "Blockchain", "q14_ar_vr": "Realidade aumentada/virtual",
                    "q14_nuvem": "Computação em nuvem", "q14_impressao3d": "Impressão 3D"}),
    "Q15": ("q15", {"q15_conhec_ia": "Conhecimento do funcionamento da IA"}),
    "Q16": ("q16", {"q16_freq_ia": "Frequência de uso de IA"}),
    "Q17": ("q17", {"q17_tempo_uso": "Tempo de uso de IA"}),
    "Q19": ("freq", {"q19_gen_texto": "IA generativa (texto)", "q19_gen_imagem": "IA generativa (imagens)",
                     "q19_gen_video": "IA generativa (vídeos)", "q19_outras": "Outras ferramentas de IA"}),
    "Q20": ("freq", {"q20_chatgpt": "ChatGPT", "q20_gemini": "Gemini", "q20_copilot": "Copilot",
                     "q20_claude": "Claude", "q20_perplexity": "Perplexity", "q20_characterai": "Character.ai",
                     "q20_poe": "Poe", "q20_replika": "Replika"}),
    "Q22": ("q22", {"q22_importancia": "Importância atual da IA"}),
    "Q24": ("q24", {"q24_educacao": "Educação e docência", "q24_economia": "Economia e trabalho",
                    "q24_pesq_geral": "Pesquisa científica (geral)",
                    "q24_pesq_area": "Pesquisa científica (sua área)",
                    "q24_politica": "Política e democracia", "q24_relacoes": "Relações pessoais e afetividade"}),
    "Q25": ("q25", {"q25_pesq_geral": "Pesquisa científica (geral)",
                    "q25_pesq_area": "Pesquisa científica (sua área)",
                    "q25_economia": "Economia e trabalho", "q25_educacao": "Educação e docência",
                    "q25_politica": "Política e democracia", "q25_relacoes": "Relações pessoais e afetividade"}),
    "Q26": ("q26", {"q26_cotidiano": "Parte do cotidiano (uso pessoal e produtivo)",
                    "q26_pesquisa_auto": "Pesquisa científica automatizada",
                    "q26_agi": "Capacidades intelectuais gerais humanas",
                    "q26_superinteligencia": "Superinteligência",
                    "q26_emocional": "Capacidades emocionais e afetivas"}),
}
SO_USUARIOS = {"Q17", "Q19", "Q20", "Q22"}

def base_de(q):
    return usu if q in SO_USUARIOS else d

def rotulado(df, var, escala):
    """Série com rótulos; NaN vira 'Não sei responder' (só quando a pessoa respondeu)."""
    s = df[var].map(R[escala])
    return s.fillna("Não sei responder")

# ------------------------------------------------------------------ tabelas de frequência
linhas, medias = [], []
for q, (esc, itens) in ITENS.items():
    df = base_de(q)
    ordem = list(R[esc].values()) + ["Não sei responder"]
    for var, rot in itens.items():
        s = rotulado(df, var, esc)
        for cat in ordem:
            reg = {"questão": q, "item": rot, "categoria": cat}
            for g in GRUPOS + ["Total"]:
                m = (df.grupo == g) if g != "Total" else pd.Series(True, index=df.index)
                n = int((s[m] == cat).sum())
                reg[f"{g} n"] = n
                reg[f"{g} %"] = round(100 * n / m.sum(), 1)
            if any(reg[f"{g} n"] for g in GRUPOS):
                linhas.append(reg)
        reg = {"questão": q, "item": rot, "escala": " / ".join(f"{k}={v}" for k, v in R[esc].items())}
        for g in GRUPOS + ["Total"]:
            m = (df.grupo == g) if g != "Total" else pd.Series(True, index=df.index)
            reg[f"{g} média"] = round(df.loc[m, var].mean(), 2)
            reg[f"{g} n válido"] = int(df.loc[m, var].notna().sum())
        medias.append(reg)
freq_tab = pd.DataFrame(linhas)
med_tab = pd.DataFrame(medias)

def multipla(cols_rot, base, nome_q):
    out = []
    for var, rot in cols_rot.items():
        reg = {"questão": nome_q, "opção": rot}
        for g in GRUPOS + ["Total"]:
            m = (base.grupo == g) if g != "Total" else pd.Series(True, index=base.index)
            reg[f"{g} n"] = int(base.loc[m, var].sum())
            reg[f"{g} %"] = round(100 * base.loc[m, var].mean(), 1)
        out.append(reg)
    return pd.DataFrame(out).sort_values("Total %", ascending=False)

Q18 = {"q18_revisao": "Revisão textual", "q18_buscas": "Buscas e verificações simples",
       "q18_estudo": "Estudo aprofundado de temas", "q18_traducao": "Tradução textual",
       "q18_automacao": "Automação de tarefas", "q18_bibliografica": "Pesquisa bibliográfica",
       "q18_analise_exploratoria": "Análise exploratória de dados",
       "q18_artisticas": "Atividades artísticas e criativas", "q18_design_pesquisa": "Design de pesquisa",
       "q18_obtencao_dados": "Obtenção e produção de dados",
       "q18_programacao": "Programação e software", "q18_orientacao_pessoal": "Orientação pessoal e psicológica",
       "q18_analise_avancada": "Análise avançada de dados", "q18_outra": "Outra"}
q18_tab = multipla(Q18, usu, "Q18")

Q12 = {c: c.replace("q12_", "").replace("_", " ") for c in d.columns
       if c.startswith("q12_") and c != "q12_total"}
q12_tab = multipla(Q12, d, "Q12")

q21_cols = [c for c in d.columns if c.startswith("q21_") and c not in
            ("q21_citou", "q21_ferramentas", "q21_texto")]
q21_tab = multipla({c: c.replace("q21_", "") for c in q21_cols}, usu, "Q21")
q21_tab.insert(2, "obs", "% dos usuários de IA")

q23 = usu["q23_intencao"].fillna("Não sei responder")
q23_tab = pd.crosstab(q23, usu.grupo, margins=True, margins_name="Total")
q23_tab = q23_tab.reindex(Q23_ORD + ["Não sei responder", "Total"])
q23_pct = (100 * q23_tab / q23_tab.loc["Total"]).round(1)
q23_tab = pd.concat({"n": q23_tab, "%": q23_pct}, axis=1)

# Q24 x Q25: mapa intensidade x valência por área
AREAS = ["economia", "educacao", "pesq_geral", "pesq_area", "politica", "relacoes"]
NOME_AREA = {"economia": "Economia e trabalho", "educacao": "Educação e docência",
             "pesq_geral": "Pesquisa (geral)", "pesq_area": "Pesquisa (sua área)",
             "politica": "Política e democracia", "relacoes": "Relações e afetividade"}
mapa = []
for a in AREAS:
    for g in GRUPOS + ["Total"]:
        m = (d.grupo == g) if g != "Total" else pd.Series(True, index=d.index)
        v = d.loc[m, f"q25_{a}"]
        mapa.append({"área": NOME_AREA[a], "grupo": g,
                     "intensidade média (0-4)": round(d.loc[m, f"q24_{a}"].mean(), 2),
                     "valência média (-2 a +2)": round(v.mean(), 2),
                     "% negativo": round(100 * (v < 0).sum() / v.notna().sum(), 1),
                     "% positivo": round(100 * (v > 0).sum() / v.notna().sum(), 1),
                     "% não sei (valência)": round(100 * v.isna().mean(), 1)})
mapa_tab = pd.DataFrame(mapa)

idx = ["idx_fluencia", "idx_programacao", "idx_emergentes", "idx_uso_ia", "n_chatbots",
       "idx_intensidade_impacto", "idx_valencia_impacto", "idx_ceticismo_capacidades"]
idx_tab = d.groupby("grupo")[idx].agg(["mean", "median", "std", "count"]).T.round(2)
idx_tab["Total"] = pd.concat([d[idx].mean(), d[idx].median(), d[idx].std(), d[idx].count()],
                             keys=["mean", "median", "std", "count"]).swaplevel().reindex(idx_tab.index).round(2)

with pd.ExcelWriter(OUT / "04_descritiva_tabelas.xlsx", engine="openpyxl") as xw:
    pd.DataFrame({"nota": [
        "Percentuais dentro de cada grupo. Docentes n=89, estudantes n=317.",
        "Q17-Q23 apenas usuários de IA: docentes n=%d, estudantes n=%d." % (NU["Docente"], NU["Estudante"]),
        "Médias excluem 'Não sei responder'."]}).to_excel(xw, sheet_name="LEIA", index=False)
    freq_tab.to_excel(xw, sheet_name="T1_frequencias", index=False)
    med_tab.to_excel(xw, sheet_name="T2_medias_itens", index=False)
    q12_tab.to_excel(xw, sheet_name="T3_Q12_softwares", index=False)
    q18_tab.to_excel(xw, sheet_name="T4_Q18_atividades_IA", index=False)
    q21_tab.to_excel(xw, sheet_name="T5_Q21_outras_ferramentas", index=False)
    q23_tab.to_excel(xw, sheet_name="T6_Q23_intencao")
    mapa_tab.to_excel(xw, sheet_name="T7_mapa_impactos", index=False)
    idx_tab.to_excel(xw, sheet_name="T8_indices_por_grupo")

# ------------------------------------------------------------------ gráficos
def empilhado(ax, linhas_rot, dados_pct, cores, cats, rot_cat=True):
    """dados_pct: DataFrame linhas x categorias (%), já ordenado."""
    esq = np.zeros(len(linhas_rot))
    for cat, cor in zip(cats, cores):
        v = dados_pct[cat].values
        ax.barh(range(len(linhas_rot)), v, left=esq, color=cor, height=0.62,
                edgecolor=SURF, linewidth=1.2, label=cat)
        for i, (x0, w) in enumerate(zip(esq, v)):
            if w >= 7:
                ax.text(x0 + w / 2, i, f"{w:.0f}", ha="center", va="center", fontsize=8,
                        color="#ffffff" if lum(cor) < 0.45 else INK)
        esq += v
    ax.set_yticks(range(len(linhas_rot)), linhas_rot)
    if not ax.yaxis_inverted():          # eixos compartilhados: inverter só uma vez
        ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    eixo_limpo(ax, grade=None)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", length=0)

def pct_por_grupo(df, var, esc):
    s = rotulado(df, var, esc)
    cats = list(R[esc].values()) + ["Não sei responder"]
    t = pd.crosstab(df.grupo, s, normalize="index").reindex(columns=cats, fill_value=0) * 100
    return t.reindex(GRUPOS), cats

def legenda(fig, ax, ncol):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    y0 = min(inv.transform((0, a.get_tightbbox(r).y0))[1] for a in fig.axes)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.0, y0 - 0.01), ncol=ncol, frameon=False,
               fontsize=8.5, labelcolor=INK2, handlelength=1.2, columnspacing=1.2)

# 1) Painel de uma variável ordinal por grupo (Q15, Q16, Q22)
def painel_grupos(var, esc, titulo, nome, base, cores):
    t, cats = pct_por_grupo(base, var, esc)
    if t["Não sei responder"].sum() == 0:
        cats = cats[:-1]
    else:
        cores = cores + [NSR]
    n = {g: int((base.grupo == g).sum()) for g in GRUPOS}
    fig, ax = plt.subplots(figsize=(8, 2.0))
    empilhado(ax, [f"Docentes (n={n['Docente']})", f"Estudantes (n={n['Estudante']})"],
              t, cores, cats)
    ax.set_title(titulo)
    legenda(fig, ax, ncol=min(len(cats), 3))
    salvar(fig, nome, "Valores em % dentro do grupo.")

painel_grupos("q16_freq_ia", "q16", "Frequência de uso de IA (Q16)", "04_q16_frequencia.png", d, SEQ5[:])
painel_grupos("q15_conhec_ia", "q15", "Conhecimento sobre o funcionamento da IA (Q15)",
              "04_q15_conhecimento.png", d, SEQ5[:])
painel_grupos("q22_importancia", "q22", "Importância atual da IA na vida pessoal e profissional (Q22)",
              "04_q22_importancia.png", usu, SEQ5[:])

# 2) Itens empilhados (todos os respondentes / usuários), um painel por grupo
def itens_por_grupo(q, titulo, nome, cores, ordenar_por=None, nota=""):
    esc, itens = ITENS[q]
    base = base_de(q)
    cats = list(R[esc].values()) + ["Não sei responder"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 0.48 * len(itens) + 1.6), sharey=True)
    tabs = {}
    for g in GRUPOS:
        b = base[base.grupo == g]
        t = pd.DataFrame({rot: rotulado(b, var, esc).value_counts(normalize=True) * 100
                          for var, rot in itens.items()}).T.reindex(columns=cats, fill_value=0).fillna(0)
        tabs[g] = t
    ordem = list(itens.values())
    if ordenar_por:
        ordem = (tabs["Docente"] + tabs["Estudante"])[ordenar_por].sum(axis=1).sort_values(ascending=False).index.tolist()
    usa_nsr = any(tabs[g]["Não sei responder"].sum() > 0 for g in GRUPOS)
    cs = cats if usa_nsr else cats[:-1]
    cores_ = cores + ([NSR] if usa_nsr else [])
    for ax, g in zip(axs, GRUPOS):
        empilhado(ax, ordem, tabs[g].loc[ordem], cores_, cs)
        nb = int((base.grupo == g).sum())
        ax.set_title(f"{g}s (n={nb})", fontsize=10.5)
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout()
    legenda(fig, axs[0], ncol=min(len(cs), 6))
    salvar(fig, nome, "Valores em % dentro do grupo. " + nota)

itens_por_grupo("Q20", "Frequência de uso de chatbots (Q20)", "04_q20_chatbots.png",
                ["#d6d5cf"] + SEQ4,
                ordenar_por=["Frequentemente", "Muito frequentemente", "Eventualmente"],
                nota="Apenas usuários de IA.")
itens_por_grupo("Q19", "Frequência de uso de ferramentas de IA (Q19)", "04_q19_ferramentas.png",
                ["#d6d5cf"] + SEQ4, nota="Apenas usuários de IA.")
itens_por_grupo("Q24", "Intensidade percebida dos impactos da IA (Q24)", "04_q24_intensidade.png", SEQ5,
                ordenar_por=["Altíssima"])
itens_por_grupo("Q26", "Em quanto tempo a IA… (Q26)", "04_q26_horizonte.png",
                ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#e34948"])
itens_por_grupo("Q14", "Nível de conhecimento sobre tecnologias emergentes (Q14)", "04_q14_emergentes.png",
                ["#d6d5cf"] + SEQ4)

# 3) Valência divergente (Q25), centrada no "Nulo"
def divergente(nome):
    esc, itens = ITENS["Q25"]
    cats = list(R[esc].values())
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    ordem = None
    for ax, g in zip(axs, GRUPOS):
        b = d[d.grupo == g]
        t = pd.DataFrame({rot: b[var].map(R[esc]).value_counts(normalize=True) * 100
                          for var, rot in itens.items()}).T.reindex(columns=cats, fill_value=0).fillna(0)
        nsr = pd.Series({rot: 100 * b[var].isna().mean() for var, rot in itens.items()})
        if ordem is None:
            ordem = (t["Relativamente positivo"] + t["Muito positivo"]
                     - t["Relativamente negativo"] - t["Muito negativo"]).sort_values(ascending=False).index.tolist()
        t, nsr = t.loc[ordem], nsr.loc[ordem]
        y = np.arange(len(ordem))
        neg_ini = -(t["Muito negativo"] + t["Relativamente negativo"] + t["Nulo"] / 2)
        esq = neg_ini.values.copy()
        for cat, cor in zip(cats, DIV5):
            w = t[cat].values
            ax.barh(y, w, left=esq, color=cor, height=0.62, edgecolor=SURF, linewidth=1.2, label=cat)
            for i, (x0, ww) in enumerate(zip(esq, w)):
                if ww >= 7:
                    ax.text(x0 + ww / 2, i, f"{ww:.0f}", ha="center", va="center", fontsize=8,
                            color="#ffffff" if lum(cor) < 0.45 else INK)
            esq += w
        for i, v in enumerate(nsr.values):
            ax.text(101, i, f"NS {v:.0f}%", va="center", fontsize=7.5, color=MUTED)
        ax.axvline(0, color=BASE, linewidth=1)
        ax.set_yticks(y, ordem)
        if not ax.yaxis_inverted():
            ax.invert_yaxis()
        ax.set_xlim(-100, 112)
        ax.set_xticks([-50, 0, 50])
        ax.xaxis.set_major_formatter(lambda v, _: f"{abs(v):.0f}%")
        eixo_limpo(ax, grade="x")
        ax.set_title(f"{g}s (n={NG[g]})", fontsize=10.5)
    fig.suptitle("Valência dos impactos da IA por área (Q25)", x=0.01, ha="left",
                 fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout()
    legenda(fig, axs[0], ncol=5)
    salvar(fig, nome, "% entre quem opinou; barras centradas no 'Nulo'. NS = % 'Não sei responder' no grupo.")

divergente("04_q25_valencia.png")

# 4) Barras agrupadas por grupo (Q18 atividades, Q23 intenção, Q21 ferramentas)
def barras_grupo(tab, col_rot, titulo, nome, nota, base_n):
    tab = tab.copy()
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(tab) + 1.4))
    h = 0.38
    y = np.arange(len(tab))
    xmax = tab[[f"{g} %" for g in GRUPOS]].values.max()
    for k, g in enumerate(GRUPOS):
        pos = y + (k - 0.5) * (h + 0.02)
        ax.barh(pos, tab[f"{g} %"], height=h, color=COR[g], label=f"{g}s (n={base_n[g]})")
        for p, v in zip(pos, tab[f"{g} %"]):
            ax.text(v + xmax * 0.01, p, f"{v:.0f}%", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(y, tab[col_rot])
    ax.invert_yaxis()
    ax.set_xlim(0, tab[[f"{g} %" for g in GRUPOS]].values.max() * 1.15)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title(titulo)
    ax.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=INK2)
    eixo_limpo(ax)
    salvar(fig, nome, nota)

barras_grupo(q18_tab, "opção", "Atividades em que usa IA (Q18)", "04_q18_atividades.png",
             "Múltipla escolha; % dos usuários de IA em cada grupo.", NU)
q23p = q23_tab["%"].drop("Total").reset_index().rename(columns={"index": "opção", "q23_intencao": "opção"})
q23p.columns = ["opção"] + [f"{c} %" for c in q23p.columns[1:]]
barras_grupo(q23p, "opção", "Intenção de uso futuro da IA (Q23)", "04_q23_intencao.png",
             "% dos usuários de IA em cada grupo.", NU)
q21p = q21_tab[q21_tab["Total n"] >= 3].copy()
q21p["opção"] = q21p["opção"].map({
    "notebooklm": "NotebookLM", "deepseek": "DeepSeek", "gamma": "Gamma", "manus": "Manus",
    "grok": "Grok", "scispace": "SciSpace", "adobe": "Adobe (Firefly, Photoshop…)",
    "ferramentas_de_literatura": "Busca de literatura (Elicit, Litmaps…)",
    "consensus": "Consensus"}).fillna(q21p["opção"])
barras_grupo(q21p, "opção", "Outras ferramentas citadas espontaneamente (Q21)", "04_q21_outras.png",
             "Resposta aberta; ferramentas citadas por 3 ou mais pessoas; % dos usuários de IA.", NU)

# 5) Mapa intensidade x valência por área
fig, ax = plt.subplots(figsize=(7.5, 5))
mt = mapa_tab[mapa_tab.grupo != "Total"]
for a in AREAS:
    sub = mt[mt["área"] == NOME_AREA[a]]
    ax.plot(sub["valência média (-2 a +2)"], sub["intensidade média (0-4)"], color=BASE, linewidth=1, zorder=1)
for g in GRUPOS:
    sub = mt[mt.grupo == g]
    ax.scatter(sub["valência média (-2 a +2)"], sub["intensidade média (0-4)"], s=70, color=COR[g],
               edgecolor=SURF, linewidth=2, zorder=2, label=f"{g}s")
tot = mapa_tab[mapa_tab.grupo == "Total"]
for _, r in tot.iterrows():
    ax.annotate(r["área"], (r["valência média (-2 a +2)"], r["intensidade média (0-4)"]),
                xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5, color=INK2,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none", alpha=0.85))
ax.axvline(0, color=BASE, linewidth=1)
ax.set_xlabel("Valência média (−2 muito negativo … +2 muito positivo)")
ax.set_ylabel("Intensidade média (0 nenhuma … 4 altíssima)")
ax.set_title("Intensidade × valência dos impactos, por área")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(True, color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
lim = max(abs(mt["valência média (-2 a +2)"]).max() * 1.35, 0.8)
ax.set_xlim(-lim, lim)
ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="lower left")
salvar(fig, "04_mapa_impactos.png", "Linhas ligam docentes e estudantes na mesma área.")

# ------------------------------------------------------------------ console
pd.set_option("display.width", 220)
print(med_tab.drop(columns="escala").to_string(index=False))
print(q18_tab.to_string(index=False))
print(q23_tab.to_string())
print(mapa_tab.to_string(index=False))
print(q21_tab[q21_tab["Total n"] > 0].to_string(index=False))
print(idx_tab.to_string())
