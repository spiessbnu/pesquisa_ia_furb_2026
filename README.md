# Percepções e usos da Inteligência Artificial na FURB

Material de análise da pesquisa *Percepções e usos da Inteligência Artificial (IA) na Universidade Regional de Blumenau* (projeto PIBIC 168/2025).

A pesquisa foi conduzida pelo NET – Núcleo de Estudos da Tecnociência, associado ao Programa de Pós-Graduação em Desenvolvimento Regional e ao Departamento de Ciências Sociais e Filosofia da FURB.

- **Coordenador:** Maiko Rafael Spiess
- **Bolsista PIBIC/CNPq:** Ana Maria Eigen Facchini Dognini

## A pesquisa

- Questionário on-line anônimo (Microsoft Forms, 26 questões).
- Aplicado a docentes e estudantes da FURB entre 25/11/2025 e 13/04/2026.
- 406 respostas válidas: 89 docentes e 317 estudantes.

O [relatório de resultados](relatorio/Relatorio_IA_FURB_2026.pdf) (PDF) descreve o instrumento, os procedimentos, os resultados e as limitações.

## O que está neste repositório

| Pasta ou arquivo | Conteúdo |
|---|---|
| `relatorio/Relatorio_IA_FURB_2026.pdf` | Relatório de resultados, versão para divulgação |
| `analise/01_limpeza.py` … `06_revisao_final.py` | Scripts da análise, a executar nessa ordem |
| `analise/livro_de_codigos.md` | Codificação das variáveis e decisões da coordenação |
| `analise/resultados/*.xlsx` | Tabelas agregadas de cada etapa (amostra, índices, descritiva, testes, modelos e checagens) |
| `analise/resultados/figuras/` | Gráficos gerados pelos scripts |
| `requirements.txt` | Pacotes Python usados |

## O que não está, e por quê

Os **microdados não são divulgados**. Isso inclui a planilha exportada do Forms e as bases `base_limpa` e `base_indices`.

O formulário não registrou nome nem e-mail. Mesmo assim, algumas combinações de características de perfil (departamento, vínculo, gênero e faixa etária) bastam para singularizar pessoas dentro da instituição. Por isso, a equipe se comprometeu a publicar apenas resultados agregados, como está registrado na seção de aspectos éticos do relatório.

Pelo mesmo motivo, as contagens por curso e por departamento, que têm vários casos com uma só pessoa, foram retiradas de `02_amostra_tabelas.xlsx`. O script `02_descricao_amostra.py` ainda as gera para uso interno da equipe.

Sem a base, os scripts não podem ser executados. Eles ficam disponíveis para documentar com exatidão como cada resultado foi produzido.

## Como reproduzir (com acesso autorizado à base)

1. Coloque a planilha exportada do Forms (`Percepções e usos da Inteligência Artificial … .xlsx`) na raiz do repositório.
2. Instale os pacotes com Python 3.13: `pip install -r requirements.txt`.
3. Execute os scripts na ordem, a partir da raiz:

```bash
python -P analise/01_limpeza.py
python -P analise/02_descricao_amostra.py
python -P analise/03_indices.py
python -P analise/04_descritiva.py
python -P analise/05_inferencial.py
python -P analise/06_revisao_final.py
```

Os scripts criam `analise/dados/` (microdados, ignorada pelo Git) e atualizam `analise/resultados/`.

## Como citar

SPIESS, Maiko Rafael; DOGNINI, Ana Maria Eigen Facchini. *Percepções e usos da Inteligência Artificial na Universidade Regional de Blumenau*: relatório de resultados. Blumenau: FURB, Núcleo de Estudos da Tecnociência, 2026.

## Licença

- **Código** (`analise/*.py` e `requirements.txt`): licença MIT. Veja [`LICENSE`](LICENSE).
- **Textos, tabelas e figuras** (o relatório em `relatorio/`, este README, o livro de códigos e o conteúdo de `analise/resultados/`): licença [Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.pt-br). Veja [`LICENSE-CC-BY-4.0.txt`](LICENSE-CC-BY-4.0.txt). Ao reutilizar esse material, cite a pesquisa como indicado acima.

## Uso de IA

Foram usados o ChatGPT e o Claude na análise estatística, na produção dos gráficos e na diagramação. Todos os resultados foram conferidos pela equipe.
