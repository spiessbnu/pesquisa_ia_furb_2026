"""
Etapa 6 - Checagens da revisão final (sensibilidade, testes complementares, confiabilidade)
Uso:  python analise/06_revisao_final.py   (requer base_indices gerada por 03_indices.py)
Gera: analise/resultados/06_revisao_tabelas.xlsx

Conteúdo
- Confiabilidade: alfa da intensidade de uso só entre usuários; fluência com e sem o item invertido.
- Sensibilidade do coeficiente "docente" na valência (M4): idade categórica, sem uso e fluência,
  só usuários, sem a variável de onda.
- Faixa de 30 a 49 anos: diferença docente - estudante na valência (IC 95%) e na intenção de
  ampliar (Fisher, qui² com e sem correção, IC 95% da diferença de proporções).
- Q23 x grupo: teste exato por simulação (Monte Carlo) e versão com "usar menos" + "parar".
- Gênero entre docentes no índice de tecnologias emergentes: IC 95% bootstrap do r.
- Tamanho das famílias de testes na correção de Benjamini-Hochberg (05_inferencial.py).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
warnings.simplefilter("ignore")
RAIZ = Path(__file__).resolve().parent
d = pd.read_excel(RAIZ / "dados" / "base_indices.xlsx", sheet_name="dados")
OUT = RAIZ / "resultados"
rng = np.random.default_rng(20261122)


def alfa(X):
    X = X.dropna()
    k = X.shape[1]
    return k / (k - 1) * (1 - X.var(ddof=1).sum() / X.sum(axis=1).var(ddof=1)), len(X)


def pomp(s, mn, mx):
    return (s - mn) / (mx - mn) * 100


# ------------------------------------------------------------------ 1) confiabilidade
usu = d[d.usuario_ia == 1]
Xu = pd.DataFrame({"q16": pomp(usu.q16_freq_ia, 0, 4), "q19": pomp(usu.q19_gen_texto, 0, 4),
                   "q18": pomp(usu.q18_total, 0, 14)})
Xt = pd.DataFrame({"q16": pomp(d.q16_freq_ia, 0, 4), "q19": pomp(d.q19_gen_texto, 0, 4),
                   "q18": pomp(d.q18_total, 0, 14)})
flu4 = ["q11_conhecimento", "q11_acompanha", "q11_facilidade", "q11_interesse_inv"]
conf = pd.DataFrame([
    {"medida": "Intensidade de uso (todos, com não usuários = 0)", "alfa": alfa(Xt)[0], "n": alfa(Xt)[1]},
    {"medida": "Intensidade de uso (só usuários)", "alfa": alfa(Xu)[0], "n": alfa(Xu)[1]},
    {"medida": "Fluência, 4 itens (com 'pouco interesse' invertido)", "alfa": alfa(d[flu4])[0],
     "n": alfa(d[flu4])[1]},
    {"medida": "Fluência, 3 itens (sem o invertido)", "alfa": alfa(d[flu4[:3]])[0], "n": alfa(d[flu4[:3]])[1]},
])
conf["alfa"] = conf.alfa.round(3)
r_inv = d[flu4].corr().loc["q11_interesse_inv", flu4[:3]].round(2)

# ------------------------------------------------------------------ 2) sensibilidade do M4
d["docente"] = (d.grupo == "Docente").astype(int)
d["feminino"] = d.genero.map({"Feminino": 1, "Masculino": 0})
d["onda2"] = (d.inicio >= "2026-02-01").astype(int)
base = d.dropna(subset=["idx_valencia_impacto", "feminino", "faixa_etaria_n", "idx_uso_ia",
                        "idx_fluencia", "idx_programacao", "idx_intensidade_impacto"]).copy()
for c in ["idx_uso_ia", "idx_fluencia", "idx_programacao", "idx_intensidade_impacto"]:
    base[c + "_10"] = base[c] / 10
M4 = ("idx_valencia_impacto ~ docente + feminino + faixa_etaria_n + idx_uso_ia_10 + idx_fluencia_10"
      " + idx_programacao_10 + idx_intensidade_impacto_10 + onda2")
espec = {
    "M1 só grupo (diferença bruta)": ("idx_valencia_impacto ~ docente", base),
    "M2 grupo + gênero + idade (efeito total, sem uso e fluência)":
        ("idx_valencia_impacto ~ docente + feminino + faixa_etaria_n", base),
    "M4 original (idade linear)": (M4, base),
    "M4 com idade categórica": (M4.replace("faixa_etaria_n", "C(faixa_etaria_n)"), base),
    "M4 sem uso e fluência": (M4.replace(" + idx_uso_ia_10 + idx_fluencia_10", ""), base),
    "M4 só usuários de IA": (M4, base[base.usuario_ia == 1]),
    "M4 sem onda": (M4.replace(" + onda2", ""), base),
}
sens = []
for nome, (f, b) in espec.items():
    m = smf.ols(f, b).fit(cov_type="HC3")
    ci = m.conf_int().loc["docente"]
    sens.append({"especificação": nome, "coef docente": m.params["docente"], "IC95 inf": ci[0],
                 "IC95 sup": ci[1], "p": m.pvalues["docente"], "n": int(m.nobs), "R² aj.": m.rsquared_adj})
sens = pd.DataFrame(sens).round(3)
m4 = smf.ols(M4, base).fit(cov_type="HC3")
m4_tab = pd.DataFrame({"coef": m4.params, "IC95 inf": m4.conf_int()[0], "IC95 sup": m4.conf_int()[1],
                       "p": m4.pvalues}).round(3)
# idade categórica: coeficientes por faixa
mcat = smf.ols(M4.replace("faixa_etaria_n", "C(faixa_etaria_n)"), base).fit(cov_type="HC3")
idade_cat = mcat.params.filter(like="faixa").round(3)

# ------------------------------------------------------------------ 3) faixa de 30 a 49 anos
f = d[d.faixa_etaria == "Entre 30 e 49 anos"]
fv = f.dropna(subset=["idx_valencia_impacto"])
mv = smf.ols("idx_valencia_impacto ~ docente", fv).fit(cov_type="HC3")
fu = f[(f.usuario_ia == 1) & f.q23_intencao.notna()]
amp = (fu.q23_intencao == "Ampliar").astype(int)
t = pd.crosstab(fu.docente, amp).loc[[1, 0], [1, 0]].values
p_fisher = stats.fisher_exact(t)[1]
p_chi = stats.chi2_contingency(t, correction=False)[1]
p_chi_yates = stats.chi2_contingency(t, correction=True)[1]
p1, n1 = t[0, 0] / t[0].sum(), t[0].sum()
p2, n2 = t[1, 0] / t[1].sum(), t[1].sum()
ep = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
faixa = pd.DataFrame([
    {"medida": "Valência (índice): docente − estudante", "valor": mv.params["docente"],
     "IC95 inf": mv.conf_int().loc["docente", 0], "IC95 sup": mv.conf_int().loc["docente", 1],
     "p": mv.pvalues["docente"], "n": int(mv.nobs),
     "detalhe": f"docentes {fv[fv.docente == 1].idx_valencia_impacto.mean():.2f} (n={int(fv.docente.sum())}); "
                f"estudantes {fv[fv.docente == 0].idx_valencia_impacto.mean():.2f} (n={int((1 - fv.docente).sum())})"},
    {"medida": "Ampliar o uso: docente − estudante (p.p.)", "valor": 100 * (p1 - p2),
     "IC95 inf": 100 * (p1 - p2 - 1.96 * ep), "IC95 sup": 100 * (p1 - p2 + 1.96 * ep),
     "p": p_fisher, "n": int(n1 + n2),
     "detalhe": f"docentes {t[0, 0]}/{n1} ({100 * p1:.1f}%); estudantes {t[1, 0]}/{n2} ({100 * p2:.1f}%); "
                f"Fisher p={p_fisher:.3f}; qui² p={p_chi:.3f}; qui² c/ Yates p={p_chi_yates:.3f}"},
]).round(3)

# ------------------------------------------------------------------ 4) Q23 x grupo
u = d[(d.usuario_ia == 1) & d.q23_intencao.notna()]
ct = pd.crosstab(u.grupo, u.q23_intencao)
chi2_obs, p_asym, _, esp = stats.chi2_contingency(ct)
g, y = u.grupo.values, u.q23_intencao.values
sims = np.array([stats.chi2_contingency(pd.crosstab(rng.permutation(g), y))[0] for _ in range(20000)])
p_mc = (1 + (sims >= chi2_obs).sum()) / (1 + len(sims))
y4 = np.where(np.isin(y, ["Usar menos", "Parar"]), "Usar menos ou parar", y)
ct4 = pd.crosstab(g, y4)
chi4, p4, _, esp4 = stats.chi2_contingency(ct4)
q23 = pd.DataFrame([
    {"teste": "Q23 (categorias originais) x grupo, qui² assintótico", "qui²": chi2_obs, "p": p_asym,
     "menor esperada": esp.min(), "V de Cramér": np.sqrt(chi2_obs / ct.values.sum())},
    {"teste": "Q23 x grupo, teste exato por simulação (20 000 permutações)", "qui²": chi2_obs, "p": p_mc,
     "menor esperada": esp.min(), "V de Cramér": np.sqrt(chi2_obs / ct.values.sum())},
    {"teste": "Q23 com 'usar menos' + 'parar' agrupados", "qui²": chi4, "p": p4,
     "menor esperada": esp4.min(), "V de Cramér": np.sqrt(chi4 / ct4.values.sum())},
]).round(4)
dist23 = pd.crosstab(d.loc[d.usuario_ia == 1, "q23_intencao"].fillna("Sem resposta"),
                     d.loc[d.usuario_ia == 1, "grupo"])
dist23_pct = (100 * dist23 / dist23.sum()).round(1)

# ------------------------------------------------------------------ 5) gênero entre docentes, emergentes
dd = d[(d.grupo == "Docente") & d.genero.isin(["Feminino", "Masculino"])].dropna(subset=["idx_emergentes"])
a, b = dd.loc[dd.genero == "Feminino", "idx_emergentes"].values, dd.loc[dd.genero == "Masculino", "idx_emergentes"].values


def rbis(a, b):
    return 2 * stats.mannwhitneyu(a, b).statistic / (len(a) * len(b)) - 1


boot = [rbis(rng.choice(a, len(a)), rng.choice(b, len(b))) for _ in range(5000)]
gen_doc = pd.DataFrame([{"medida": "Tecnologias emergentes (com IA), docentes F x M", "média F": a.mean(),
                         "média M": b.mean(), "n F": len(a), "n M": len(b), "r": rbis(a, b),
                         "IC95 inf": np.percentile(boot, 2.5), "IC95 sup": np.percentile(boot, 97.5)}]).round(3)

# ------------------------------------------------------------------ 6) famílias da correção BH
fam = pd.DataFrame([
    {"família": "A: docentes x estudantes (índices, itens ordinais e atividades da Q18)", "testes": 53},
    {"família": "B: feminino x masculino, dentro de cada grupo", "testes": "53 por grupo"},
    {"família": "C: faixas etárias, dentro de cada grupo", "testes": "39 por grupo"},
    {"família": "D: ondas de coleta, dentro de cada grupo", "testes": "10 por grupo"},
    {"família": "F: docentes x estudantes de 30 a 49 anos", "testes": 9},
    {"família": "Q23 (A2, B2, F2) e modelos", "testes": "sem correção; p nominal"},
])

with pd.ExcelWriter(OUT / "06_revisao_tabelas.xlsx", engine="openpyxl") as xw:
    conf.to_excel(xw, sheet_name="1_confiabilidade", index=False)
    r_inv.to_frame("r com 'pouco interesse' invertido").to_excel(xw, sheet_name="1b_item_invertido")
    sens.to_excel(xw, sheet_name="2_sensibilidade_docente", index=False)
    m4_tab.to_excel(xw, sheet_name="2b_M4")
    idade_cat.to_frame("coef").to_excel(xw, sheet_name="2c_idade_categorica")
    faixa.to_excel(xw, sheet_name="3_faixa_30a49", index=False)
    q23.to_excel(xw, sheet_name="4_Q23_testes", index=False)
    dist23.to_excel(xw, sheet_name="4b_Q23_n")
    dist23_pct.to_excel(xw, sheet_name="4c_Q23_pct")
    gen_doc.to_excel(xw, sheet_name="5_genero_docentes", index=False)
    fam.to_excel(xw, sheet_name="6_familias_BH", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)
for nome, tab in [("confiabilidade", conf), ("item invertido", r_inv), ("sensibilidade", sens), ("M4", m4_tab),
                  ("idade categórica", idade_cat), ("30-49", faixa), ("Q23", q23), ("Q23 n", dist23),
                  ("Q23 %", dist23_pct), ("gênero docentes", gen_doc)]:
    print(f"\n== {nome}\n{tab.to_string()}")
