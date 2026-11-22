"""
Etapa 3 - Construção de índices
Uso:  python analise/03_indices.py   (requer a base gerada por 01_limpeza.py)
Gera:
  analise/dados/base_indices.csv / .xlsx   (base limpa + índices; aba livro_indices)
  analise/resultados/03_indices_tabelas.xlsx (confiabilidade, itens, descritivas)

Regras gerais
- Índices em escala 0-100 (POMP: % do máximo possível), exceto a valência do impacto,
  que mantém a escala -2..+2 para preservar o sinal (negativo / positivo).
- Média dos itens válidos, exigindo pelo menos 2/3 dos itens respondidos
  ("Não sei responder" é ausente); abaixo disso o índice fica vazio.
- Confiabilidade: alfa de Cronbach (casos completos) e correlação item-total corrigida.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
import warnings
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
RAIZ = Path(__file__).resolve().parent
d = pd.read_excel(RAIZ / "dados" / "base_limpa.xlsx", sheet_name="dados")
OUT = RAIZ / "resultados"
OUT.mkdir(exist_ok=True)

def alfa(X):
    X = X.dropna()
    k = X.shape[1]
    if k < 2 or len(X) < 3:
        return np.nan, len(X)
    return k / (k - 1) * (1 - X.var(ddof=1).sum() / X.sum(axis=1).var(ddof=1)), len(X)

def pomp(s, mn, mx):
    return (s - mn) / (mx - mn) * 100

def media_min(X, prop=2 / 3):
    ok = X.notna().sum(axis=1) >= np.ceil(prop * X.shape[1])
    return X.mean(axis=1).where(ok)

# ------------------------------------------------------------------ variáveis auxiliares
q20 = [c for c in d.columns if c.startswith("q20_")]
d["n_chatbots"] = (d[q20] > 0).sum(axis=1)

# ------------------------------------------------------------------ definição dos índices
# nome: (itens, min, max, escala_saida, descrição, base)
IND = {
    "idx_fluencia": (["q11_conhecimento", "q11_acompanha", "q11_facilidade", "q11_interesse_inv"],
                     1, 5, "pomp", "Fluência tecnológica autopercebida (Q11, 4 itens; "
                     "'pouco interesse' invertido)"),
    "idx_programacao": (["q13_webdesign", "q13_programacao", "q13_bancodados"],
                        0, 4, "pomp", "Domínio de programação e dados (Q13: web design, "
                        "linguagens, bancos de dados). Computação em nuvem ficou fora: "
                        "baixa correlação com os demais (alfa sobe de 0,87 para 0,92 sem ela)"),
    "idx_emergentes": (["q14_ia", "q14_iot", "q14_blockchain", "q14_ar_vr", "q14_nuvem", "q14_impressao3d"],
                       0, 4, "pomp", "Conhecimento de tecnologias emergentes (Q14, 6 itens, "
                       "incluindo IA; decisão da coordenação, 22/11/2026)"),
    "idx_uso_ia": (["q16_freq_ia", "q19_gen_texto", "q18_total"],
                   None, None, "pomp_itens", "Intensidade de uso de IA: média de frequência "
                   "geral (Q16, 0-4), frequência de IA generativa de texto (Q19, 0-4) e "
                   "diversidade de atividades (Q18, 0-13 + outra), cada um convertido a 0-100. "
                   "Inclui não usuários (= 0)"),
    "idx_intensidade_impacto": ([c for c in d.columns if c.startswith("q24_")],
                                0, 4, "pomp", "Intensidade percebida dos impactos da IA (Q24, "
                                "6 áreas)"),
    "idx_valencia_impacto": ([c for c in d.columns if c.startswith("q25_")],
                             -2, 2, "original", "Valência dos impactos da IA (Q25, 6 áreas): "
                             "-2 muito negativo ... 0 nulo ... +2 muito positivo"),
    "idx_ceticismo_capacidades": (["q26_agi", "q26_superinteligencia", "q26_emocional"],
                                  1, 5, "pomp", "Distância percebida até capacidades humanas "
                                  "(Q26: inteligência geral, superinteligência, emoções). "
                                  "0 = imediatamente ... 100 = nunca"),
}
POMP_ITENS = {"q16_freq_ia": (0, 4), "q19_gen_texto": (0, 4), "q18_total": (0, 14)}

conf, itens_tab, livro = [], [], []
for nome, (itens, mn, mx, escala, desc) in IND.items():
    X = d[itens].astype(float)
    if escala == "pomp_itens":
        X = pd.DataFrame({c: pomp(X[c], *POMP_ITENS[c]) for c in itens})
    a, n_a = alfa(X)
    m = media_min(X)
    if escala == "pomp":
        m = pomp(m, mn, mx)
    d[nome] = m.round(2)
    ev = np.linalg.eigvalsh(X.dropna().corr().values)[::-1]
    conf.append({"índice": nome, "itens": len(itens), "alfa": round(a, 3), "n (completos)": n_a,
                 "n (com índice)": int(m.notna().sum()),
                 "1º autovalor": round(ev[0], 2), "2º autovalor": round(ev[1], 2),
                 "% variância 1º fator": round(100 * ev[0] / len(itens), 1)})
    for c in itens:
        resto = [x for x in itens if x != c]
        itens_tab.append({"índice": nome, "item": c,
                          "média": round(d[c].mean(), 2), "dp": round(d[c].std(), 2),
                          "n": int(d[c].notna().sum()),
                          "r item-total corrigida": round(X[c].corr(X[resto].sum(axis=1)), 2),
                          "alfa sem o item": round(alfa(X[resto])[0], 3)})
    livro.append({"variavel": nome, "itens": ", ".join(itens), "descricao": desc,
                  "escala": "-2 a +2" if escala == "original" else "0 a 100",
                  "alfa": round(a, 3)})

livro.append({"variavel": "n_chatbots", "itens": ", ".join(q20),
              "descricao": "Amplitude de ferramentas: nº de chatbots da Q20 usados ao menos "
              "'raramente'", "escala": "0 a 8", "alfa": np.nan})

conf = pd.DataFrame(conf)
itens_tab = pd.DataFrame(itens_tab)
livro = pd.DataFrame(livro)

idx_cols = list(IND) + ["n_chatbots"]
desc = d[idx_cols].describe(percentiles=[.25, .5, .75]).T.round(2)
desc.index.name = "índice"

# matriz de correlações (Spearman) entre índices e itens-chave de IA
chave = idx_cols + ["q15_conhec_ia", "q14_ia", "q17_tempo_uso", "q22_importancia"]
corr = d[chave].corr(method="spearman").round(2)

# ------------------------------------------------------------------ exportação
d.to_csv(RAIZ / "dados" / "base_indices.csv", sep=";", decimal=",", index=False,
         encoding="utf-8-sig")
livro_base = pd.read_excel(RAIZ / "dados" / "base_limpa.xlsx", sheet_name="livro_codigos")
alertas = pd.read_excel(RAIZ / "dados" / "base_limpa.xlsx", sheet_name="alertas")
with pd.ExcelWriter(RAIZ / "dados" / "base_indices.xlsx", engine="openpyxl") as xw:
    d.to_excel(xw, sheet_name="dados", index=False)
    livro_base.to_excel(xw, sheet_name="livro_codigos", index=False)
    livro.to_excel(xw, sheet_name="livro_indices", index=False)
    alertas.to_excel(xw, sheet_name="alertas", index=False)
with pd.ExcelWriter(OUT / "03_indices_tabelas.xlsx", engine="openpyxl") as xw:
    conf.to_excel(xw, sheet_name="T1_confiabilidade", index=False)
    itens_tab.to_excel(xw, sheet_name="T2_itens", index=False)
    desc.to_excel(xw, sheet_name="T3_descritivas")
    corr.to_excel(xw, sheet_name="T4_correlacoes_spearman")
    livro.to_excel(xw, sheet_name="T5_definicoes", index=False)

pd.set_option("display.width", 220)
print(conf.to_string(index=False), "\n")
print(desc.to_string(), "\n")
print(corr.to_string())
