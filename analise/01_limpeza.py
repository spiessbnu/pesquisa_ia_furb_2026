"""
Etapa 1 - Limpeza e codificação da base
Pesquisa "Percepções e usos da IA na FURB" (PIBIC 168/2025)

Uso:  python analise/01_limpeza.py
Lê a planilha original (sem alterá-la) e gera:
  analise/dados/base_limpa.csv   (UTF-8 com BOM, separador ';', decimal ',')
  analise/dados/base_limpa.xlsx  (abas: dados, livro_codigos, alertas)
"""
import re
import sys
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = next(RAIZ.glob("Percepções e usos da Inteligência Artificial*.xlsx"))
SAIDA = RAIZ / "analise" / "dados"
SAIDA.mkdir(parents=True, exist_ok=True)

raw = pd.read_excel(ORIGEM)
assert len(raw.columns) == 67, "estrutura da planilha mudou"
C = list(raw.columns)
col = lambda i: raw.iloc[:, i]

# Verificação de que os índices apontam para as perguntas esperadas
ESPERADO = {6: "Você é professor", 11: "Marque todas", 14: "Estou cursando",
            20: "Quais dos seguintes", 31: "Em relação ao funcionamento",
            32: "Com que frequência", 34: "Atualmente, para quais",
            47: "Existe alguma", 49: "No futuro", 62: "Em quanto tempo"}
for i, prefixo in ESPERADO.items():
    assert str(C[i]).startswith(prefixo), (i, C[i])

livro = []   # (variavel, questao, descricao, codificacao)
def doc(var, q, desc, cod=""):
    livro.append((var, q, desc, cod))

def limpa(s):
    if pd.isna(s):
        return np.nan
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or np.nan

df = pd.DataFrame(index=raw.index)

# ---------------------------------------------------------------- identificação
df["id"] = col(0)
df["inicio"] = pd.to_datetime(col(1))
df["fim"] = pd.to_datetime(col(2))
df["duracao_min"] = ((df["fim"] - df["inicio"]).dt.total_seconds() / 60).round(2)
doc("id", "-", "ID da resposta no MS Forms")
doc("inicio / fim", "-", "Data e hora de início e término")
doc("duracao_min", "-", "Tempo de preenchimento em minutos")

# ---------------------------------------------------------------- Q1 grupo
df["grupo"] = col(6).map({"Professor(a)": "Docente", "Estudante": "Estudante"})
assert df["grupo"].notna().all()
doc("grupo", "Q1", "Professor(a) ou estudante", "Docente / Estudante")
doc_ = df["grupo"] == "Docente"

# ---------------------------------------------------------------- perfil unificado
def genero(v):
    v = limpa(v)
    if pd.isna(v):
        return np.nan
    k = v.lower()
    if k in ("feminino",):
        return "Feminino"
    if k in ("masculino", "macho"):
        return "Masculino"
    return "Outro / não binário"

df["genero"] = np.where(doc_, col(7).map(genero), col(12).map(genero))
df["genero_original"] = np.where(doc_, col(7), col(12))
doc("genero", "Q2/Q7", "Gênero (docentes e estudantes unificados)",
    "Feminino / Masculino / Outro / não binário ('macho' -> Masculino; "
    "não binário, neutro, fluido, agênero -> Outro / não binário)")
doc("genero_original", "Q2/Q7", "Gênero como digitado (para conferência)")

FAIXAS = ["Menos de 20 anos", "Entre 20 e 29 anos", "Entre 30 e 49 anos",
          "Entre 50 e 59 anos", "Mais de 59 anos"]
fx = np.where(doc_, col(8).map(limpa), col(13).map(limpa))
df["faixa_etaria"] = pd.Categorical(fx, categories=FAIXAS, ordered=True)
df["faixa_etaria_n"] = df["faixa_etaria"].cat.codes.replace(-1, np.nan) + 1
doc("faixa_etaria", "Q3/Q8", "Faixa etária (categorias ordenadas)", " < ".join(FAIXAS))
doc("faixa_etaria_n", "Q3/Q8", "Faixa etária numérica", "1=<20 ... 5=>59")

# ---------------------------------------------------------------- docentes
df["doc_departamento"] = col(9).map(limpa)
df["doc_vinculo"] = col(10).map(limpa).replace({
    "PSPS/contrato emergencial": "PSPS/emergencial",
    "Tempo Parcial Horista (TPH)": "TPH",
    "Tempo Integral (TI) ou Dedicação Exclusiva (DE)": "TI/DE",
})
VINC_PADRAO = {"PSPS/emergencial", "TPH", "TI/DE"}
df.loc[doc_ & ~df["doc_vinculo"].isin(VINC_PADRAO), "doc_vinculo_cat"] = "Outro"
df.loc[doc_ & df["doc_vinculo"].isin(VINC_PADRAO), "doc_vinculo_cat"] = df["doc_vinculo"]
doc("doc_departamento", "Q4", "Departamento do docente (texto)")
doc("doc_vinculo", "Q5", "Vínculo do docente (texto, rótulos abreviados)")
doc("doc_vinculo_cat", "Q5", "Vínculo agrupado", "PSPS/emergencial / TPH / TI/DE / Outro")

ATIV = {"Docência na graduação": "doc_ativ_graduacao",
        "Docência na pós-graduação": "doc_ativ_pos",
        "Pesquisa": "doc_ativ_pesquisa",
        "Extensão": "doc_ativ_extensao",
        "Cargos de gestão e/ou chefia": "doc_ativ_gestao"}

def separa(v):
    if pd.isna(v):
        return []
    return [limpa(p) for p in str(v).split(";") if limpa(p) is not np.nan and limpa(p)]

partes6 = col(11).map(separa)
for rot, var in ATIV.items():
    df[var] = np.where(doc_, partes6.map(lambda ps: int(rot in ps)), np.nan)
    doc(var, "Q6", f"Atividade: {rot}", "1=marcou, 0=não (vazio p/ estudantes)")
df["doc_ativ_outra_txt"] = partes6.map(
    lambda ps: "; ".join(p for p in ps if p not in ATIV) or np.nan)
df["doc_ativ_outra"] = np.where(doc_, df["doc_ativ_outra_txt"].notna().astype(int), np.nan)
doc("doc_ativ_outra / _txt", "Q6", "Outra atividade (indicador e texto)")

# ---------------------------------------------------------------- estudantes
NIVEL = {"Graduação": "Graduação",
         "Pós-graduação lato sensu (especialização)": "Especialização",
         "Pós-graduação (Mestrado)": "Mestrado",
         "Pós-graduação (Doutorado)": "Doutorado",
         "Sou aluno/a especial ou similar": "Aluno especial"}
df["est_nivel"] = col(14).map(limpa).map(NIVEL)
df["est_curso"] = col(15).map(limpa)
# padroniza grafias do curso
df["est_curso"] = df["est_curso"].replace({
    "educação": "Educação",
    "Pós Graduação em Engenharia Florestal": "Pós-Graduação em Engenharia Florestal",
    "Pós-Graduação em Ciencias Ambientais": "Pós-Graduação em Ciências Ambientais",
})
doc("est_nivel", "Q9", "Nível do estudante",
    "Graduação / Especialização / Mestrado / Doutorado / Aluno especial")
doc("est_curso", "Q10", "Curso do estudante (grafias padronizadas)")

# Variáveis de comparação (decisão da coordenação, 21/11/2026): apenas `grupo`
# (Docente x Estudante, com estudantes de todos os níveis juntos), `genero` e
# `faixa_etaria`. Nível do estudante, vínculo e atividades docentes ficam na base
# só para descrever a amostra, sem servir de segmentação.

# Sem agrupamento por grande área (decisão da coordenação, 21/11/2026): a amostra
# não foi estratificada por curso/departamento e uma classificação adequada exigiria
# considerar a estrutura interna da FURB. Curso e departamento ficam como informados.

# ---------------------------------------------------------------- Q11 fluência
LIK = {"Discordo totalmente": 1, "Discordo parcialmente": 2, "Neutro": 3,
       "Concordo parcialmente": 4, "Concordo totalmente": 5}
Q11 = {16: "q11_conhecimento", 17: "q11_acompanha", 18: "q11_facilidade",
       19: "q11_pouco_interesse"}
for i, v in Q11.items():
    df[v] = col(i).map(limpa).map(LIK)
    doc(v, "Q11", C[i].strip(), "1=Discordo totalmente ... 5=Concordo totalmente")
df["q11_interesse_inv"] = 6 - df["q11_pouco_interesse"]
doc("q11_interesse_inv", "Q11", "Item 'pouco interesse' invertido (= interesse)",
    "6 - q11_pouco_interesse")

# ---------------------------------------------------------------- Q12 softwares
SOFT = {"Redes sociais": "q12_redes_sociais", "Plataformas de comunicação": "q12_comunicacao",
        "Processadores de texto": "q12_texto", "Apresentações": "q12_apresentacoes",
        "Planilhas": "q12_planilhas", "Ferramentas de edição de imagem": "q12_edicao_imagem",
        "Ferramentas de gerenciamento": "q12_gestao_projetos",
        "Plataformas de armazenamento": "q12_nuvem", "Plataformas de programação": "q12_programacao",
        "Sistema de informação geográfica": "q12_sig", "Análise de dados estatísticos": "q12_estatistica",
        "Ferramentas de Desenho Assistido": "q12_cad", "Software para desenvolvimento de jogos": "q12_jogos"}
partes12 = col(20).map(separa)
for pref, var in SOFT.items():
    df[var] = partes12.map(lambda ps: int(any(p.startswith(pref) for p in ps)))
    doc(var, "Q12", f"Usa regularmente: {pref}...", "1=marcou, 0=não")
df["q12_total"] = df[list(SOFT.values())].sum(axis=1)
doc("q12_total", "Q12", "Número de tipos de software usados", "0-13")
naoreconh = partes12.map(lambda ps: [p for p in ps if not any(p.startswith(k) for k in SOFT)])
assert naoreconh.map(len).sum() == 0, naoreconh[naoreconh.map(len) > 0]

# ---------------------------------------------------------------- Q13/Q14 domínio
DOM = {"Nenhum": 0, "Baixo": 1, "Médio": 2, "Alto": 3, "Profissional": 4,
       "Não sei responder": np.nan}
Q13 = {21: "q13_webdesign", 22: "q13_programacao", 23: "q13_bancodados", 24: "q13_nuvem"}
Q14 = {25: "q14_ia", 26: "q14_iot", 27: "q14_blockchain", 28: "q14_ar_vr",
       29: "q14_nuvem", 30: "q14_impressao3d"}
for q, mapa in (("Q13", Q13), ("Q14", Q14)):
    for i, v in mapa.items():
        s = col(i).map(limpa)
        assert s.isin(DOM).all(), s[~s.isin(DOM)].unique()
        df[v] = s.map(DOM)
        doc(v, q, C[i].strip(), "0=Nenhum 1=Baixo 2=Médio 3=Alto 4=Profissional; "
            "'Não sei responder' = vazio")

# ---------------------------------------------------------------- Q15-Q17
Q15 = {"Desconheço completamente seu funcionamento": 0,
       "Possuo apenas conhecimentos básicos": 1,
       "Possuo conhecimentos intermediários": 2,
       "Possuo conhecimentos avançados": 3,
       "Possuo conhecimentos muito avançados, em nível de desenvolvimento e criação de IAs": 4}
df["q15_conhec_ia"] = col(31).map(limpa).map(Q15)
doc("q15_conhec_ia", "Q15", "Conhecimento sobre o funcionamento da IA",
    "0=Desconhece 1=Básico 2=Intermediário 3=Avançado 4=Muito avançado")

Q16 = {"Nunca utilizo": 0, "Algumas vezes por semestre": 1, "Algumas vezes por mês": 2,
       "Algumas vezes por semana": 3, "Diariamente": 4}
df["q16_freq_ia"] = col(32).map(limpa).map(Q16)
df["usuario_ia"] = (df["q16_freq_ia"] > 0).astype(int)
doc("q16_freq_ia", "Q16", "Frequência de uso de IA",
    "0=Nunca 1=Semestre 2=Mês 3=Semana 4=Diariamente")
doc("usuario_ia", "Q16", "Usa IA (Q16 diferente de 'Nunca utilizo')",
    "1=sim, 0=não. Os não usuários (n=21) pularam as Q17-Q23 no formulário")
nao_usu = df["usuario_ia"] == 0

Q17 = {"Há menos de um ano": 1, "Entre 1 e 2 anos": 2, "Entre 2 e 3 anos": 3,
       "Há mais de 3 anos": 4, "Não sei responder": np.nan}
df["q17_tempo_uso"] = col(33).map(limpa).map(Q17)
doc("q17_tempo_uso", "Q17", "Há quanto tempo usa IA",
    "1=<1 ano 2=1-2 3=2-3 4=>3 anos; NSR e não usuários = vazio")

# ---------------------------------------------------------------- Q18 atividades
ATIV18 = {"Buscas e verificações simples": "q18_buscas",
          "Estudo aprofundado de temas de interesse": "q18_estudo",
          "Design de pesquisa": "q18_design_pesquisa",
          "Pesquisa bibliográfica e bibliométrica": "q18_bibliografica",
          "Revisão textual": "q18_revisao",
          "Tradução textual": "q18_traducao",
          "Obtenção e produção de dados": "q18_obtencao_dados",
          "Análise exploratória de dados": "q18_analise_exploratoria",
          "Técnicas avançadas de análise de dados": "q18_analise_avancada",
          "Auxílio na programação de computadores e desenvolvimento de software": "q18_programacao",
          "Automação de tarefas": "q18_automacao",
          "Atividades artísticas e criativas": "q18_artisticas",
          "Orientação pessoal e psicológica": "q18_orientacao_pessoal"}
partes18 = col(34).map(separa)
for rot, var in ATIV18.items():
    df[var] = partes18.map(lambda ps: int(rot in ps))
    doc(var, "Q18", f"Usa IA para: {rot}", "1=marcou, 0=não (não usuários = 0)")
df["q18_marcou_nao_utiliza"] = partes18.map(lambda ps: int("Não utilizo nenhum recurso de IA" in ps))
df["q18_outra_txt"] = partes18.map(lambda ps: "; ".join(
    p for p in ps if p not in ATIV18 and p != "Não utilizo nenhum recurso de IA") or np.nan)
df["q18_outra"] = df["q18_outra_txt"].notna().astype(int)
df["q18_total"] = df[list(ATIV18.values())].sum(axis=1) + df["q18_outra"]
doc("q18_marcou_nao_utiliza", "Q18", "Marcou 'Não utilizo nenhum recurso de IA'",
    "1=sim. Inconsistente com Q16 quando usuario_ia=1 (ver alertas)")
doc("q18_outra / _txt", "Q18", "Outra atividade (indicador e texto)")
doc("q18_total", "Q18", "Número de atividades em que usa IA", "0-14")

# ---------------------------------------------------------------- Q19/Q20 frequência
FREQ = {"Nunca": 0, "Raramente": 1, "Eventualmente": 2, "Frequentemente": 3,
        "Muito frequentemente": 4, "Não sei responder": np.nan}
Q19 = {35: "q19_gen_texto", 36: "q19_gen_imagem", 37: "q19_gen_video", 38: "q19_outras"}
Q20 = {39: "q20_chatgpt", 40: "q20_claude", 41: "q20_gemini", 42: "q20_copilot",
       43: "q20_perplexity", 44: "q20_replika", 45: "q20_characterai", 46: "q20_poe"}
for q, mapa in (("Q19", Q19), ("Q20", Q20)):
    for i, v in mapa.items():
        s = col(i).map(limpa)
        assert s.dropna().isin(FREQ).all(), s[~s.isin(FREQ)].unique()
        df[v] = s.map(FREQ)
        df.loc[nao_usu, v] = 0   # quem nunca usa IA tem frequência zero por definição
        doc(v, q, C[i].strip(), "0=Nunca 1=Raramente 2=Eventualmente 3=Frequentemente "
            "4=Muito frequentemente; NSR = vazio; não usuários = 0")

# ---------------------------------------------------------------- Q21 texto livre
FERRAM = {"NotebookLM": r"no+te?bo+k\s*\.?\s*(lm|ia)",
          "DeepSeek": r"deeps[ea]+k",
          "Gamma": r"\bgamma",
          "Manus": r"\bmanus",
          "Grok": r"\bgrok",
          "SciSpace": r"scispace",
          "Consensus": r"consensus",
          "ChatPDF": r"chatpdf",
          "Canva": r"\bcanva\b",
          "Adobe (Firefly/Photoshop/Podcast)": r"adobe|firefly|photoshop",
          "Freepik": r"freepik",
          "Teachy": r"teachy",
          "Ferramentas de literatura (Elicit, Litmaps, Research Rabbit, Connected Papers, Paperpal)":
              r"elicit|litmaps|research rabbit|connected papers|paperpal",
          "Outras": None}
NADA = re.compile(r"^(n|n[aã]o|nenhuma|\.|no momento n[aã]o)\.?$|^n[aã]o,", re.I)

def q21(v):
    v = limpa(v)
    if pd.isna(v):
        return np.nan, np.nan
    if NADA.match(v):
        return 0, np.nan
    achou = [k for k, rx in FERRAM.items() if rx and re.search(rx, v, re.I)]
    return 1, "; ".join(achou) if achou else "Outras"

r21 = col(47).map(q21)
df["q21_citou"] = r21.map(lambda t: t[0])
df["q21_ferramentas"] = r21.map(lambda t: t[1])
df["q21_texto"] = col(47).map(limpa)
for k in FERRAM:
    if k == "Outras":
        continue
    nome = "q21_" + re.sub(r"[^a-z0-9]+", "_",
                           unicodedata.normalize("NFKD", k.split(" (")[0].lower())
                           .encode("ascii", "ignore").decode()).strip("_")
    df[nome] = df["q21_ferramentas"].fillna("").str.contains(re.escape(k)).astype(int)
    doc(nome, "Q21", f"Citou {k}", "1=sim")
doc("q21_citou", "Q21", "Citou alguma outra ferramenta",
    "1=sim, 0=respondeu não/nenhuma, vazio=não respondeu")
doc("q21_ferramentas", "Q21", "Ferramentas identificadas (categorização automática por palavra-chave)")
doc("q21_texto", "Q21", "Resposta original")

# ---------------------------------------------------------------- Q22/Q23
Q22 = {"Insignificantes": 0, "Pouco importantes": 1, "Moderadamente importantes": 2,
       "Muito importantes": 3, "Indispensáveis": 4}
df["q22_importancia"] = col(48).map(limpa).map(Q22)
doc("q22_importancia", "Q22", "Importância atual da IA",
    "0=Insignificantes ... 4=Indispensáveis; não usuários = vazio")

Q23 = {"Parar de utilizar": "Parar", "Usar menos": "Usar menos",
       "Manter a quantidade de uso atual": "Manter", "Ampliar o uso": "Ampliar",
       "Continuar usando, mas de formas diferentes": "Formas diferentes",
       "Não sei responder / não quero responder": np.nan}
df["q23_intencao"] = col(49).map(limpa).map(Q23)
df["q23_intencao_ord"] = df["q23_intencao"].map(
    {"Parar": -2, "Usar menos": -1, "Manter": 0, "Formas diferentes": 0, "Ampliar": 1})
doc("q23_intencao", "Q23", "Intenção futura de uso (nominal)",
    "Parar / Usar menos / Manter / Ampliar / Formas diferentes; NSR = vazio")
doc("q23_intencao_ord", "Q23", "Intenção futura (direção do uso)",
    "-2=Parar -1=Usar menos 0=Manter ou formas diferentes +1=Ampliar")

# ---------------------------------------------------------------- Q24/Q25 impactos
AREAS_IMP = ["economia", "educacao", "pesq_geral", "pesq_area", "politica", "relacoes"]
INT = {"Nenhuma intensidade": 0, "Baixa intensidade": 1, "Intensidade moderada": 2,
       "Alta intensidade": 3, "Altíssima intensidade": 4, "Não sei responder": np.nan}
VAL = {"Muito negativo": -2, "Relativamente negativo": -1, "Nulo": 0,
       "Relativamente positivo": 1, "Muito positivo": 2, "Não sei responder": np.nan}
for k, a in enumerate(AREAS_IMP):
    for q, base, mapa, cod in (
            ("Q24", 50, INT, "0=Nenhuma 1=Baixa 2=Moderada 3=Alta 4=Altíssima; NSR = vazio"),
            ("Q25", 56, VAL, "-2=Muito negativo ... 0=Nulo ... +2=Muito positivo; NSR = vazio")):
        s = col(base + k).map(limpa)
        assert s.isin(mapa).all(), s[~s.isin(mapa)].unique()
        v = f"{q.lower()}_{a}"
        df[v] = s.map(mapa)
        doc(v, q, re.sub(r"2$", "", str(C[base + k])).strip(), cod)

# ---------------------------------------------------------------- Q26 horizonte
HOR = {"Imediatamente": 1, "A curto prazo": 2, "A médio prazo": 3, "A longo prazo": 4,
       "Nunca": 5, "Não sei responder": np.nan}
Q26 = {62: "q26_cotidiano", 63: "q26_pesquisa_auto", 64: "q26_agi",
       65: "q26_superinteligencia", 66: "q26_emocional"}
for i, v in Q26.items():
    s = col(i).map(limpa)
    assert s.isin(HOR).all(), s[~s.isin(HOR)].unique()
    df[v] = s.map(HOR)
    df[v + "_nunca"] = (s == "Nunca").astype(int)
    doc(v, "Q26", str(C[i]).replace("​", "").strip(),
        "1=Imediatamente 2=Curto 3=Médio 4=Longo prazo 5=Nunca; NSR = vazio")
    doc(v + "_nunca", "Q26", "Respondeu 'Nunca'", "1=sim")

# ---------------------------------------------------------------- alertas de qualidade
alertas = []
def alerta(mask, motivo):
    for i in df.index[mask]:
        alertas.append({"id": df.at[i, "id"], "motivo": motivo})
    df.loc[mask, "flag_" + re.sub(r"\W+", "_", motivo.split(":")[0].lower()).strip("_")] = 1

# Alertas apenas sinalizam; decisões da coordenação (21/11/2026): vínculos ambíguos
# permanecem como docentes e o ID 392 (preenchimento rápido) é mantido.
alerta(doc_ & (df["doc_vinculo_cat"] == "Outro"),
       "vinculo_ambiguo: docente informou vínculo fora das opções")
alerta((df["usuario_ia"] == 1) & (df["q18_marcou_nao_utiliza"] == 1),
       "inconsistencia_uso: usa IA (Q16) mas marcou 'não utilizo' na Q18")
alerta(df["duracao_min"] < 2, "preenchimento_rapido: menos de 2 minutos")
itens = [c for c in df.columns if re.match(r"q(11|13|14|16|19|20|24|25|26)_", c)
         and not c.endswith("_nunca") and c != "q11_interesse_inv"]
dup = df.duplicated(subset=itens + ["grupo", "genero", "faixa_etaria", "doc_departamento", "est_curso"], keep=False)
alerta(dup, "possivel_duplicata: respostas idênticas a outra linha")
flags = [c for c in df.columns if c.startswith("flag_")]
df[flags] = df[flags].fillna(0).astype(int)
doc("flag_*", "-", "Alertas de qualidade (1=sinalizado). Nenhuma linha foi excluída.")

# ---------------------------------------------------------------- exportação
df["faixa_etaria"] = df["faixa_etaria"].astype(str).replace("nan", np.nan)
df.to_csv(SAIDA / "base_limpa.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
livro_df = pd.DataFrame(livro, columns=["variavel", "questao", "descricao", "codificacao"])
alert_df = pd.DataFrame(alertas)
with pd.ExcelWriter(SAIDA / "base_limpa.xlsx", engine="openpyxl") as xw:
    df.to_excel(xw, sheet_name="dados", index=False)
    livro_df.to_excel(xw, sheet_name="livro_codigos", index=False)
    alert_df.to_excel(xw, sheet_name="alertas", index=False)

# ---------------------------------------------------------------- resumo
print(f"Base limpa: {df.shape[0]} linhas x {df.shape[1]} colunas")
print(df["grupo"].value_counts().to_string(), "\n")
print(df.groupby(["faixa_etaria", "grupo"], observed=False).size().unstack(fill_value=0).to_string(), "\n")
print(df["genero"].value_counts(dropna=False).to_string(), "\n")
print("Alertas:")
print(alert_df.groupby("motivo")["id"].apply(lambda s: ", ".join(map(str, s))).to_string()
      if len(alert_df) else "nenhum")
