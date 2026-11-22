# Livro de códigos: base limpa

Pesquisa *Percepções e usos da IA na FURB* (PIBIC 168/2025). Etapa 1: limpeza e codificação.

- **Script:** `analise/01_limpeza.py` (reproduzível; a planilha original não é alterada)
- **Saídas:** `analise/dados/base_limpa.csv` (UTF-8, separador `;`, decimal `,`) e `analise/dados/base_limpa.xlsx`, com as abas `dados`, `livro_codigos` (descrição de cada variável) e `alertas`. Esses arquivos são microdados e **não fazem parte deste repositório**.
- **Base:** 406 respostas × 128 variáveis, coletadas entre 25/11/2025 e 13/04/2026

## Composição

| Grupo (`grupo`) | n |
|---|---|
| Estudantes (todos os níveis: 272 de graduação, 43 de mestrado ou doutorado, 1 de especialização, 1 aluno especial) | 317 |
| Docentes | 89 |

## Variáveis de comparação

Decisão da coordenação (21/11/2026): as comparações usam **apenas** três variáveis.

| Variável | Categorias |
|---|---|
| `grupo` | Docente × Estudante (os estudantes de todos os níveis ficam juntos) |
| `genero` | Feminino / Masculino / Outro / não binário (n = 5; insuficiente para testes) |
| `faixa_etaria` | 5 faixas ordenadas |

O nível do estudante (`est_nivel`), o curso, o departamento, o vínculo docente e as atividades docentes ficam na base **apenas para descrever a amostra**. Eles não servem de segmentação.

Atenção na leitura dos resultados: faixa etária e grupo se sobrepõem bastante. 81% dos estudantes têm até 29 anos, enquanto 94% dos docentes têm 30 anos ou mais. Assim, uma diferença entre faixas etárias pode refletir, em parte, a diferença entre docentes e estudantes, e vice-versa.

## Decisões de codificação

### Perfil

- **Gênero** (Q2/Q7) foi unificado entre docentes e estudantes. "macho" passou a Masculino. As 5 respostas livres (não binário, neutro, gênero fluido, agênero) foram agrupadas em *Outro / não binário*. O texto original está em `genero_original`.
- **Faixa etária** (Q3/Q8) foi unificada. Docentes não tinham a opção "Menos de 20".
- **Curso e departamento** ficam como informados (`est_curso`, `doc_departamento`), com correção apenas de grafias, por exemplo "educação" → "Educação". **Não há agrupamento por grande área**, por decisão da coordenação (21/11/2026), por dois motivos: a amostra não foi estratificada por curso ou departamento, e uma classificação adequada precisaria considerar as especificidades da estrutura interna da FURB. Por isso, as análises não comparam cursos ou departamentos.

### Escalas (numéricas, "Não sei responder" = vazio)

| Questão | Codificação |
|---|---|
| Q11 fluência | 1 = Discordo totalmente … 5 = Concordo totalmente; o item "pouco interesse" também aparece invertido em `q11_interesse_inv` |
| Q13/Q14 domínio | 0 = Nenhum, 1 = Baixo, 2 = Médio, 3 = Alto, 4 = Profissional |
| Q15 conhecimento de IA | 0 = Desconhece … 4 = Muito avançado |
| Q16 frequência de uso | 0 = Nunca utilizo, 1 = Algumas vezes por semestre, 2 = Algumas vezes por mês, 3 = Algumas vezes por semana, 4 = Diariamente |
| Q17 tempo de uso | 1 = < 1 ano … 4 = > 3 anos |
| Q19/Q20 frequência por ferramenta | 0 = Nunca … 4 = Muito frequentemente |
| Q22 importância | 0 = Insignificantes … 4 = Indispensáveis |
| Q23 intenção futura | nominal; em `q23_intencao_ord`, −2 = Parar, −1 = Usar menos, 0 = Manter ou formas diferentes, +1 = Ampliar |
| Q24 intensidade do impacto | 0 = Nenhuma … 4 = Altíssima |
| Q25 valor do impacto | −2 = Muito negativo, 0 = Nulo, +2 = Muito positivo |
| Q26 horizonte temporal | 1 = Imediatamente, 2 = Curto, 3 = Médio, 4 = Longo prazo, 5 = Nunca; há também um indicador `_nunca` para cada item |

### Não usuários de IA

Os 21 respondentes que marcaram "Nunca utilizo" na Q16 pularam as Q17–Q23. O indicador `usuario_ia` identifica esses casos. Eles foram tratados assim:

- **Q19/Q20:** frequência codificada como 0 (Nunca), por implicação lógica.
- **Q18:** todas as atividades codificadas como 0.
- **Q17, Q22 e Q23:** ficam vazias, porque não há como inferir a resposta.

### Múltipla escolha e texto livre

- **Q6, Q12 e Q18** foram desmembradas em colunas 0/1, com contagens totais em `q12_total` e `q18_total`. As respostas "Outra" ficam em `_outra_txt`.
- **Q21** (texto livre) foi categorizada automaticamente por palavra-chave. `q21_citou` vale 1 quando a pessoa citou alguma ferramenta e 0 quando respondeu "não". Também há uma coluna 0/1 por ferramenta: NotebookLM (28), DeepSeek (16), Gamma (8), Manus (7), Grok (6), entre outras. Ferramentas citadas uma única vez entram em *Outras*.

## Alertas de qualidade (nenhuma linha foi excluída)

Os alertas ficam nas colunas `flag_*` e na aba `alertas`. Eles apenas sinalizam os casos; todos permanecem na base.

| Alerta | IDs | Decisão |
|---|---|---|
| Vínculo docente fora das opções | 27, 30, 277 ("Pós graduação", "Estudante de pós-graduação", "Mestrando"); 83 ("Voluntário ou visitante") | **Mantidos como docentes** (coordenação, 21/11/2026), de acordo com a instrução do formulário para docentes que cursam pós |
| Inconsistência de uso | 67, 124, 126, 234 | A Q16 indica uso de IA, mas a pessoa marcou "Não utilizo nenhum recurso" na Q18. Mantidos como usuários |
| Preenchimento rápido | 392 (0,65 min) | **Mantido** (coordenação, 21/11/2026) |
| Possível duplicata | — | Nenhum caso encontrado |

## Decisões da coordenação (22/11/2026)

- **Tecnologias emergentes:** o item de IA (`q14_ia`) faz parte do índice `idx_emergentes`, que tem 6 itens (α = 0,82). O `analise/03_indices.py` deste repositório já segue essa decisão. O índice não entra nos modelos, então M1 a M4 não mudam.
- **Fluência:** ficam os 4 itens, com "pouco interesse" invertido (α = 0,74; sem ele, 0,79).
- **Q23:** os percentuais e os testes usam como base os usuários que escolheram uma opção (87 docentes e 290 estudantes). Os 8 estudantes que marcaram "Não sei responder / não quero responder" ficam fora.
- **Microdados:** não serão divulgados (44 dos 89 docentes são únicos na combinação de departamento × vínculo × gênero × faixa etária).
- **Checagens da revisão final:** `analise/06_revisao_final.py` gera `resultados/06_revisao_tabelas.xlsx`, com a sensibilidade dos modelos, os testes complementares da Q23 e da faixa de 30 a 49 anos e a confiabilidade.
