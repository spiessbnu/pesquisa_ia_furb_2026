"""
Etapa 5 - Testes de diferença e modelos explicativos
Uso:  python analise/05_inferencial.py   (requer base_indices gerada por 03_indices.py)
Gera:
  analise/resultados/05_testes_tabelas.xlsx
  analise/resultados/figuras/05_*.png

Testes
- Variáveis ordinais e índices: Mann-Whitney (2 grupos) ou Kruskal-Wallis (3+),
  tamanho de efeito = correlação rank-bisserial r (positivo = 1º grupo maior) ou
  epsilon² (Kruskal-Wallis).  Referência: |r| ~0,1 pequeno, ~0,3 médio, ~0,5 grande.
- Variáveis nominais: qui-quadrado (V de Cramér) ou exato de Fisher em tabelas 2x2
  com caselas pequenas; diferença em pontos percentuais.
- Correção para múltiplos testes: Benjamini-Hochberg (FDR) dentro de cada família;
  a coluna p_ajustado é a que deve ser interpretada.
- Gênero: só Feminino x Masculino (Outro/não binário n=5 fica fora) e sempre DENTRO
  de cada grupo, porque a composição de gênero é invertida entre docentes e estudantes.
- Idade: sempre dentro do grupo, com faixas agregadas (estudantes: até 19 / 20-29 / 30+;
  docentes: até 49 / 50+).
Modelos
- MQO com erros robustos (HC3) para a valência dos impactos; modelos aninhados para
  ver o quanto a diferença docente-estudante se explica por idade, gênero e uso.
- Logit para "pretende usar menos ou parar" (apenas estudantes: nenhum docente).
- Ordered logit como checagem de robustez para a valência em Educação.
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.stdout.reconfigure(encoding="utf-8")
warnings.simplefilter("ignore")
RAIZ = Path(__file__).resolve().parent
d = pd.read_excel(RAIZ / "dados" / "base_indices.xlsx", sheet_name="dados")
OUT = RAIZ / "resultados"
FIG = OUT / "figuras"

# ------------------------------------------------------------------ variáveis derivadas
d["docente"] = (d.grupo == "Docente").astype(int)
d["feminino"] = d.genero.map({"Feminino": 1, "Masculino": 0})          # Outro -> NaN
d["onda"] = np.where(d.inicio < "2026-02-01", "1ª onda (nov-dez/25)", "2ª onda (mar-abr/26)")
d["onda2"] = (d.onda.str.startswith("2")).astype(int)
fx = d.faixa_etaria_n
d["idade_cat"] = np.where(d.grupo == "Estudante",
                          pd.cut(fx, [0, 1, 2, 5], labels=["Até 19", "20-29", "30 ou mais"]).astype(str),
                          pd.cut(fx, [0, 3, 5], labels=["Até 49", "50 ou mais"]).astype(str))
d["reduzir"] = d.q23_intencao.isin(["Usar menos", "Parar"]).astype(float)
d["ampliar"] = (d.q23_intencao == "Ampliar").astype(float)
d.loc[d.q23_intencao.isna(), ["reduzir", "ampliar"]] = np.nan
d.loc[d.usuario_ia == 0, ["reduzir", "ampliar"]] = np.nan

ROT = {
    "idx_fluencia": "Índice: fluência tecnológica", "idx_programacao": "Índice: programação e dados",
    "idx_emergentes": "Índice: tecnologias emergentes", "idx_uso_ia": "Índice: intensidade de uso de IA",
    "n_chatbots": "Nº de chatbots usados", "q18_total": "Nº de atividades com IA (Q18)",
    "idx_intensidade_impacto": "Índice: intensidade dos impactos",
    "idx_valencia_impacto": "Índice: valência dos impactos",
    "idx_ceticismo_capacidades": "Índice: ceticismo sobre capacidades humanas",
    "q15_conhec_ia": "Q15 conhecimento do funcionamento da IA", "q14_ia": "Q14 conhecimento de IA",
    "q16_freq_ia": "Q16 frequência de uso", "q17_tempo_uso": "Q17 tempo de uso",
    "q22_importancia": "Q22 importância atual",
    "q19_gen_texto": "Q19 IA gen. texto", "q19_gen_imagem": "Q19 IA gen. imagens",
    "q19_gen_video": "Q19 IA gen. vídeos",
    "q20_chatgpt": "Q20 ChatGPT", "q20_gemini": "Q20 Gemini", "q20_copilot": "Q20 Copilot",
    "q20_claude": "Q20 Claude", "q20_perplexity": "Q20 Perplexity",
}
for a, n in {"economia": "Economia e trabalho", "educacao": "Educação e docência",
             "pesq_geral": "Pesquisa (geral)", "pesq_area": "Pesquisa (sua área)",
             "politica": "Política e democracia", "relacoes": "Relações e afetividade"}.items():
    ROT[f"q24_{a}"] = f"Q24 intensidade: {n}"
    ROT[f"q25_{a}"] = f"Q25 valência: {n}"
for v, n in {"q26_cotidiano": "cotidiano", "q26_pesquisa_auto": "pesquisa automatizada",
             "q26_agi": "inteligência geral", "q26_superinteligencia": "superinteligência",
             "q26_emocional": "capacidades emocionais"}.items():
    ROT[v] = f"Q26 prazo: {n}"
ORDINAIS = list(ROT)
Q18 = {c: c.replace("q18_", "Q18 ").replace("_", " ") for c in d.columns
       if c.startswith("q18_") and c not in ("q18_total", "q18_outra_txt", "q18_marcou_nao_utiliza")}
SO_USU = {"q17_tempo_uso", "q22_importancia"} | {c for c in ORDINAIS if c.startswith(("q19_", "q20_"))} \
    | set(Q18) | {"q18_total"}

# ------------------------------------------------------------------ funções de teste
def mw(a, b):
    a, b = a.dropna(), b.dropna()
    if len(a) < 5 or len(b) < 5:
        return dict(n1=len(a), n2=len(b), p=np.nan, efeito=np.nan)
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return dict(n1=len(a), n2=len(b), mediana1=a.median(), mediana2=b.median(),
                media1=round(a.mean(), 2), media2=round(b.mean(), 2),
                p=p, efeito=round(2 * u / (len(a) * len(b)) - 1, 3))

def kw(grupos):
    gs = [g.dropna() for g in grupos]
    h, p = stats.kruskal(*gs)
    n = sum(len(g) for g in gs)
    return dict(p=p, efeito=round((h - len(gs) + 1) / (n - len(gs)), 3),
                **{f"media_{i + 1}": round(g.mean(), 2) for i, g in enumerate(gs)},
                **{f"n_{i + 1}": len(g) for i, g in enumerate(gs)})

def prop(a, b):
    a, b = a.dropna(), b.dropna()
    t = np.array([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]])
    if (stats.contingency.expected_freq(t) < 5).any():
        _, p = stats.fisher_exact(t)
        teste = "Fisher"
    else:
        _, p, _, _ = stats.chi2_contingency(t, correction=False)
        teste = "qui²"
    return dict(n1=len(a), n2=len(b), pct1=round(100 * a.mean(), 1), pct2=round(100 * b.mean(), 1),
                p=p, efeito=round(100 * (a.mean() - b.mean()), 1), teste=teste)

def fdr(df):
    ok = df.p.notna()
    df.loc[ok, "p_ajustado"] = multipletests(df.loc[ok, "p"], method="fdr_bh")[1]
    df["sig"] = np.select([df.p_ajustado < .001, df.p_ajustado < .01, df.p_ajustado < .05],
                          ["***", "**", "*"], "")
    df["p"] = df.p.round(4)
    df["p_ajustado"] = df.p_ajustado.round(4)
    return df

def comparar(base, col, g1, g2, rot1, rot2, variaveis=None):
    linhas = []
    for v in (variaveis or ORDINAIS):
        b = base[base.usuario_ia == 1] if v in SO_USU else base
        r = mw(b.loc[b[col] == g1, v], b.loc[b[col] == g2, v])
        linhas.append({"variável": ROT[v], "teste": "Mann-Whitney", **r})
    for v, rot in Q18.items():
        b = base[base.usuario_ia == 1]
        r = prop(b.loc[b[col] == g1, v], b.loc[b[col] == g2, v])
        linhas.append({"variável": rot, **r})
    out = fdr(pd.DataFrame(linhas))
    return out.rename(columns={"n1": f"n {rot1}", "n2": f"n {rot2}", "media1": f"média {rot1}",
                               "media2": f"média {rot2}", "mediana1": f"mediana {rot1}",
                               "mediana2": f"mediana {rot2}", "pct1": f"% {rot1}", "pct2": f"% {rot2}"})

# ------------------------------------------------------------------ A) Docentes x Estudantes
A = comparar(d, "grupo", "Docente", "Estudante", "doc", "est")
A = A.rename(columns={"efeito": "efeito (r ou dif. p.p.; + = docentes maior)"})

u = d[d.usuario_ia == 1]
ct = pd.crosstab(u.grupo, u.q23_intencao)
chi2, p23, dof, _ = stats.chi2_contingency(ct)
v23 = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))
A_q23 = pd.DataFrame([
    {"teste": "Q23 intenção (5 categorias) x grupo: qui²", "estatística": round(chi2, 2), "gl": dof,
     "p": p23, "V de Cramér": round(v23, 3)},
    {"teste": "Q23 'ampliar' x grupo", **prop(u.loc[u.grupo == "Docente", "ampliar"],
                                               u.loc[u.grupo == "Estudante", "ampliar"])},
    {"teste": "Q23 'usar menos/parar' x grupo", **prop(u.loc[u.grupo == "Docente", "reduzir"],
                                                       u.loc[u.grupo == "Estudante", "reduzir"])},
])

# ------------------------------------------------------------------ B) Gênero dentro do grupo
B = []
for g in ["Docente", "Estudante"]:
    t = comparar(d[d.grupo == g], "genero", "Feminino", "Masculino", "F", "M")
    t.insert(0, "grupo", g)
    B.append(t.rename(columns={"efeito": "efeito (r ou dif. p.p.; + = feminino maior)"}))
B = pd.concat(B)
Bq23 = []
for g in ["Docente", "Estudante"]:
    b = u[u.grupo == g]
    for alvo in ["ampliar", "reduzir"]:
        Bq23.append({"grupo": g, "teste": f"Q23 '{alvo}' F x M",
                     **prop(b.loc[b.genero == "Feminino", alvo], b.loc[b.genero == "Masculino", alvo])})
Bq23 = pd.DataFrame(Bq23)

# ------------------------------------------------------------------ C) Idade dentro do grupo
C = []
est = d[d.grupo == "Estudante"]
cats_e = ["Até 19", "20-29", "30 ou mais"]
for v in ORDINAIS:
    b = est[est.usuario_ia == 1] if v in SO_USU else est
    C.append({"grupo": "Estudante", "variável": ROT[v], "teste": "Kruskal-Wallis (até 19 / 20-29 / 30+)",
              **kw([b.loc[b.idade_cat == c, v] for c in cats_e])})
doc = d[d.grupo == "Docente"]
for v in ORDINAIS:
    b = doc[doc.usuario_ia == 1] if v in SO_USU else doc
    r = mw(b.loc[b.idade_cat == "50 ou mais", v], b.loc[b.idade_cat == "Até 49", v])
    C.append({"grupo": "Docente", "variável": ROT[v], "teste": "Mann-Whitney (50+ x até 49; + = 50+ maior)",
              "p": r["p"], "efeito": r["efeito"], "media_1": r.get("media1"), "media_2": r.get("media2"),
              "n_1": r["n1"], "n_2": r["n2"]})
C = pd.DataFrame(C)
C = pd.concat([fdr(C[C.grupo == g].copy()) for g in ["Estudante", "Docente"]])
C = C.rename(columns={"efeito": "efeito (epsilon² ou r)"})
Cq23 = pd.crosstab(u.loc[u.grupo == "Estudante", "idade_cat"],
                   u.loc[u.grupo == "Estudante", "reduzir"], normalize="index").round(3) * 100

# ------------------------------------------------------------------ D) Ondas de coleta
D = []
for g in ["Docente", "Estudante"]:
    vv = [v for v in ORDINAIS if v.startswith("idx_") or v in ("n_chatbots", "q16_freq_ia", "q22_importancia")]
    t = comparar(d[d.grupo == g], "onda", "2ª onda (mar-abr/26)", "1ª onda (nov-dez/25)", "onda2", "onda1",
                 variaveis=vv)
    t = t[~t["variável"].str.startswith("Q18 ")]          # mantém só índices e itens-chave
    t = fdr(t.drop(columns=["p_ajustado", "sig"]))
    t.insert(0, "grupo", g)
    D.append(t.rename(columns={"efeito": "efeito (r; + = 2ª onda maior)"}))
D = pd.concat(D)

# ------------------------------------------------------------------ E) Modelos
def tabela_modelo(m, nome):
    ci = m.conf_int()
    t = pd.DataFrame({"modelo": nome, "termo": m.params.index, "coef": m.params.round(3),
                      "ep (robusto)": m.bse.round(3), "IC95 inf": ci[0].round(3), "IC95 sup": ci[1].round(3),
                      "p": m.pvalues.round(4)})
    t["n"] = int(m.nobs)
    if hasattr(m, "rsquared_adj"):
        t["R² aj."] = round(m.rsquared_adj, 3)
    if hasattr(m, "prsquared"):
        t["pseudo-R²"] = round(m.prsquared, 3)
    return t.reset_index(drop=True)

# E1) valência dos impactos: modelos aninhados (mesma amostra)
base_m = d.dropna(subset=["idx_valencia_impacto", "feminino", "faixa_etaria_n", "idx_uso_ia",
                          "idx_fluencia", "idx_programacao", "idx_intensidade_impacto"]).copy()
for c in ["idx_uso_ia", "idx_fluencia", "idx_programacao", "idx_intensidade_impacto"]:
    base_m[c + "_10"] = base_m[c] / 10                     # coeficiente por 10 pontos
forms = {
    "M1 grupo": "idx_valencia_impacto ~ docente",
    "M2 + gênero e idade": "idx_valencia_impacto ~ docente + feminino + faixa_etaria_n",
    "M3 + uso e conhecimento": "idx_valencia_impacto ~ docente + feminino + faixa_etaria_n + idx_uso_ia_10"
                               " + idx_fluencia_10 + idx_programacao_10",
    "M4 + intensidade e onda": "idx_valencia_impacto ~ docente + feminino + faixa_etaria_n + idx_uso_ia_10"
                               " + idx_fluencia_10 + idx_programacao_10 + idx_intensidade_impacto_10 + onda2",
}
E1 = pd.concat([tabela_modelo(smf.ols(f, base_m).fit(cov_type="HC3"), n) for n, f in forms.items()])
X = base_m[["docente", "feminino", "faixa_etaria_n", "idx_uso_ia_10", "idx_fluencia_10",
            "idx_programacao_10", "idx_intensidade_impacto_10", "onda2"]].assign(const=1)
vif = pd.DataFrame({"variável": X.columns[:-1],
                    "VIF": [round(variance_inflation_factor(X.values, i), 2) for i in range(X.shape[1] - 1)]})

# E2) valência em educação: mesmo M4, MQO e ordered logit (robustez)
base_e = base_m.dropna(subset=["q25_educacao"]).copy()
f_ed = forms["M4 + intensidade e onda"].replace("idx_valencia_impacto", "q25_educacao")
E2 = tabela_modelo(smf.ols(f_ed, base_e).fit(cov_type="HC3"), "Educação: MQO")
preds = ["docente", "feminino", "faixa_etaria_n", "idx_uso_ia_10", "idx_fluencia_10",
         "idx_programacao_10", "idx_intensidade_impacto_10", "onda2"]
om = OrderedModel(base_e["q25_educacao"].astype(int), base_e[preds], distr="logit").fit(method="bfgs", disp=False)
E2o = pd.DataFrame({"modelo": "Educação: ordered logit", "termo": preds,
                    "coef (log-odds)": om.params[preds].round(3), "OR": np.exp(om.params[preds]).round(3),
                    "p": om.pvalues[preds].round(4), "n": int(om.nobs)}).reset_index(drop=True)

# E3) estudantes: pretende reduzir o uso
base_r = d[(d.grupo == "Estudante") & d.reduzir.notna()].dropna(
    subset=["feminino", "faixa_etaria_n", "idx_uso_ia", "idx_valencia_impacto", "q22_importancia",
            "idx_fluencia"]).copy()
for c in ["idx_uso_ia", "idx_fluencia"]:
    base_r[c + "_10"] = base_r[c] / 10
lg = smf.logit("reduzir ~ feminino + faixa_etaria_n + idx_uso_ia_10 + idx_fluencia_10 + q22_importancia"
               " + idx_valencia_impacto + onda2", base_r).fit(disp=False, cov_type="HC3")
E3 = tabela_modelo(lg, "Estudantes: usar menos/parar (logit)")
E3["OR"] = np.exp(E3.coef).round(3)
E3["OR IC95"] = [f"{np.exp(a):.2f}–{np.exp(b):.2f}" for a, b in zip(E3["IC95 inf"], E3["IC95 sup"])]

# perfil descritivo dos que pretendem reduzir
perfil_r = d[(d.grupo == "Estudante") & d.reduzir.notna()].groupby("reduzir")[
    ["idx_uso_ia", "q22_importancia", "idx_valencia_impacto", "q25_educacao", "idx_fluencia",
     "faixa_etaria_n", "feminino"]].mean().round(2)
perfil_r.index = ["Não pretende reduzir", "Pretende usar menos/parar"]

# ------------------------------------------------------------------ F) Mesma faixa etária
# Docentes e estudantes de 30 a 49 anos: separa o efeito do grupo do efeito da idade
f3049 = d[d.faixa_etaria == "Entre 30 e 49 anos"]
vv = ["idx_valencia_impacto"] + [f"q25_{a}" for a in ["educacao", "pesq_geral", "pesq_area", "economia",
                                                       "politica", "relacoes"]] + ["idx_uso_ia", "n_chatbots"]
F = comparar(f3049, "grupo", "Docente", "Estudante", "doc", "est", variaveis=vv)
F = F[~F["variável"].str.startswith("Q18 ")]
F = fdr(F.drop(columns=["p_ajustado", "sig"]))
F = F.rename(columns={"efeito": "efeito (r; + = docentes maior)"})
uf = f3049[f3049.usuario_ia == 1]
F_q23 = pd.DataFrame([{"teste": f"Q23 '{a}' docente x estudante (30-49 anos)",
                       **prop(uf.loc[uf.grupo == "Docente", a], uf.loc[uf.grupo == "Estudante", a])}
                      for a in ["ampliar", "reduzir"]])

# ------------------------------------------------------------------ exportação
with pd.ExcelWriter(OUT / "05_testes_tabelas.xlsx", engine="openpyxl") as xw:
    pd.DataFrame({"LEIA": [
        "Interpretar p_ajustado (Benjamini-Hochberg dentro de cada aba). * <.05 ** <.01 *** <.001",
        "r rank-bisserial: ~0,1 pequeno, ~0,3 médio, ~0,5 grande. Positivo = 1º grupo nomeado maior.",
        "Proporções (Q18 e Q23): efeito = diferença em pontos percentuais.",
        "Gênero: F x M dentro de cada grupo (Outro/não binário n=5 fora). Idade: dentro de cada grupo.",
        "Q17-Q23 e Q18-Q20: apenas usuários de IA.",
        "Modelos: MQO com erro robusto HC3; índices de uso, fluência, programação e intensidade "
        "entram divididos por 10 (coef = efeito de +10 pontos). faixa_etaria_n: 1 (<20) a 5 (>59)."]}
    ).to_excel(xw, sheet_name="LEIA", index=False)
    A.to_excel(xw, sheet_name="A_docente_x_estudante", index=False)
    A_q23.to_excel(xw, sheet_name="A2_Q23_grupo", index=False)
    B.to_excel(xw, sheet_name="B_genero_no_grupo", index=False)
    Bq23.to_excel(xw, sheet_name="B2_Q23_genero", index=False)
    C.to_excel(xw, sheet_name="C_idade_no_grupo", index=False)
    Cq23.to_excel(xw, sheet_name="C2_Q23_reduzir_idade_est")
    D.to_excel(xw, sheet_name="D_ondas", index=False)
    F.to_excel(xw, sheet_name="F_mesma_idade_30a49", index=False)
    F_q23.to_excel(xw, sheet_name="F2_Q23_30a49", index=False)
    E1.to_excel(xw, sheet_name="E1_modelos_valencia", index=False)
    vif.to_excel(xw, sheet_name="E1b_VIF", index=False)
    E2.to_excel(xw, sheet_name="E2_educacao_MQO", index=False)
    E2o.to_excel(xw, sheet_name="E2b_educacao_ologit", index=False)
    E3.to_excel(xw, sheet_name="E3_estud_reduzir", index=False)
    perfil_r.to_excel(xw, sheet_name="E3b_perfil_reduzir")

# ------------------------------------------------------------------ figura: modelos aninhados
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
                     "axes.edgecolor": BASE, "axes.titlecolor": INK, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "xtick.color": MUTED, "ytick.color": INK2,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "savefig.dpi": 200})
m4 = E1[E1.modelo == "M4 + intensidade e onda"].set_index("termo").drop("Intercept")
nomes = {"docente": "Docente (ref.: estudante)", "feminino": "Feminino (ref.: masculino)",
         "faixa_etaria_n": "Faixa etária (+1 faixa)", "idx_uso_ia_10": "Uso de IA (+10 pts)",
         "idx_fluencia_10": "Fluência tecnológica (+10 pts)", "idx_programacao_10": "Programação (+10 pts)",
         "idx_intensidade_impacto_10": "Intensidade percebida (+10 pts)", "onda2": "2ª onda de coleta"}
m4 = m4.loc[list(nomes)]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axs[0]
y = np.arange(len(m4))
cores = np.where(m4.p < .05, "#2a78d6", "#a9a8a2")
ax.hlines(y, m4["IC95 inf"], m4["IC95 sup"], color=cores, linewidth=2)
ax.scatter(m4.coef, y, color=cores, s=60, zorder=3, edgecolor=SURF, linewidth=1.5)
ax.axvline(0, color=BASE, linewidth=1)
ax.set_yticks(y, [nomes[t] for t in m4.index])
ax.invert_yaxis()
ax.set_xlabel("Efeito na valência (escala −2 a +2), IC 95%", color=INK2)
ax.set_title(f"Preditores da valência dos impactos (M4, n={int(m4.n.iloc[0])})", fontsize=11)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
ax = axs[1]
dk = E1[E1.termo == "docente"].reset_index(drop=True)
y = np.arange(len(dk))
cores_dk = np.where(dk.p < .05, "#2a78d6", "#a9a8a2")
ax.hlines(y, dk["IC95 inf"], dk["IC95 sup"], color=cores_dk, linewidth=2)
ax.scatter(dk.coef, y, color=cores_dk, s=60, zorder=3, edgecolor=SURF, linewidth=1.5)
for i, r in dk.iterrows():
    ax.text(r["IC95 sup"] + 0.03, i, f"{r.coef:+.2f}", va="center", fontsize=8.5, color=INK2)
ax.axvline(0, color=BASE, linewidth=1)
ax.set_yticks(y, dk.modelo)
ax.invert_yaxis()
ax.set_xlabel("Diferença docente − estudante, IC 95%", color=INK2)
ax.set_title("Diferença docente nos modelos aninhados", fontsize=11)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.text(0.01, -0.03, "Fonte: Pesquisa Percepções e usos da IA na FURB (PIBIC 168/2025). MQO com erros robustos "
         "(HC3); mesma amostra em todos os modelos. Azul = p < 0,05.", color=MUTED, fontsize=8)
fig.savefig(FIG / "05_modelo_valencia.png", bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ console
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)
def mostra(t, cols):
    print(t[[c for c in cols if c in t.columns]].to_string(index=False))
print("== A docente x estudante (significativos)")
mostra(A[A.sig != ""], ["variável", "média doc", "média est", "% doc", "% est",
                        "efeito (r ou dif. p.p.; + = docentes maior)", "p_ajustado", "sig"])
print("\n== A não significativos:", ", ".join(A.loc[A.sig == "", "variável"]))
print(A_q23.to_string(index=False))
print("\n== B gênero (significativos)")
mostra(B[B.sig != ""], ["grupo", "variável", "média F", "média M", "% F", "% M",
                        "efeito (r ou dif. p.p.; + = feminino maior)", "p_ajustado", "sig"])
print(Bq23.to_string(index=False))
print("\n== C idade (significativos)")
mostra(C[C.sig != ""], ["grupo", "variável", "media_1", "media_2", "media_3", "efeito (epsilon² ou r)",
                        "p_ajustado", "sig"])
print(Cq23.to_string())
print("\n== D ondas (p bruto < .10)")
mostra(D[D.p < .10], ["grupo", "variável", "média onda2", "média onda1", "efeito (r; + = 2ª onda maior)",
                      "p", "p_ajustado", "sig"])
print("\n== F 30-49 anos")
mostra(F, ["variável", "n doc", "n est", "média doc", "média est", "efeito (r; + = docentes maior)",
           "p", "p_ajustado", "sig"])
print(F_q23.to_string(index=False))
print("\n== E1")
print(E1.to_string(index=False))
print(vif.to_string(index=False))
print("\n== E2")
print(E2.to_string(index=False))
print(E2o.to_string(index=False))
print("\n== E3")
print(E3.to_string(index=False))
print(perfil_r.to_string())
