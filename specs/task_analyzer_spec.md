# Especificação SDD — TaskAnalyzer

Bootcamp III · Versão 1.1 (Fase 2) · Autor: Mateus de Miranda Palma Dias

> Transposição da especificação da Fase 1 (Google Docs, versão 1.0). O conteúdo
> é o mesmo; a seção **Histórico de alterações** registra o único ajuste feito
> na Fase 2, revisado por humano antes da implementação.

## Histórico de alterações

| Versão | Data | Alteração | Motivo |
|---|---|---|---|
| 1.0 | Fase 1 | Versão inicial do contrato. | Entrega inicial. |
| 1.1 | Fase 2 | Inclusão de `TaskValidationError` (subclasse de `ValueError`) e do alias público `analyze_tasks`. | O enunciado da Fase 2 pede esses nomes. Como `TaskValidationError` herda de `ValueError` e o alias apenas delega para `analisar_tarefas`, nenhum comportamento da v1.0 muda. |

**Decisões mantidas da v1.0 (não alteradas na Fase 2):** o enunciado genérico da
Fase 2 cita `tempo_medio_conclusao_horas`, `taxa_atraso_percentual`,
`data_criacao` e retorno `0.0` para médias sem dados. Este contrato, aprovado na
Fase 1, usa `tempo_medio_dias`, `percentual_atraso`, `data_inicio` e `None`
(ausência de dados, distinta de zero — ver R08 e C09). Mudar isso exigiria nova
revisão da especificação, e as regras de contexto proíbem a IA de assumir
comportamentos fora do contrato.

---

## 1. Visão geral e contrato de negócio

### 1.1 Propósito e escopo

O TaskAnalyzer é um módulo Python que recebe uma lista de tarefas, valida seus
dados e calcula indicadores de produtividade: tempo médio de conclusão,
percentual de tarefas concluídas com atraso, totais por situação e resultados
por prioridade.

O processamento é exclusivamente em memória, sem persistência em arquivos ou
bancos de dados. Esta versão não inclui interface web, aplicativo móvel,
autenticação, gamificação ou integrações. O consumidor fornece a lista e recebe
um dicionário Python.

### 1.2 Contrato público de interface

Em `src/task_analyzer.py`:

```python
analisar_tarefas(tarefas: list[Tarefa]) -> ResultadoAnalise
analyze_tasks(tarefas: list[Tarefa]) -> ResultadoAnalise   # alias (v1.1)
class TaskValidationError(ValueError): ...                 # (v1.1)
```

`Tarefa`, `Metricas` e `ResultadoAnalise` são `TypedDict`s do mesmo módulo, com
`Literal` para os valores enumerados. A função não altera a lista nem os
dicionários recebidos. Os tipos documentam; a validação em tempo de execução
continua obrigatória.

A entrada deve ser uma lista de dicionários com exatamente os sete campos
abaixo. Campos ausentes ou desconhecidos são rejeitados. Valores não são
convertidos automaticamente.

### 1.3 Campos de entrada

| Campo | Tipo | Regra |
|---|---|---|
| `id` | `int` | Positivo e único na lista. `bool` não é aceito. |
| `titulo` | `str` | Pelo menos um caractere diferente de espaço. Texto original preservado. |
| `prioridade` | `Literal['baixa','media','alta']` | Minúsculas, sem acento. |
| `data_inicio` | `str` | `AAAA-MM-DD`, data válida do calendário. |
| `prazo` | `str` | Mesmo formato; igual ou posterior a `data_inicio`. |
| `data_conclusao` | `str \| None` | Data válida ≥ `data_inicio` quando `status='concluida'`; `None` nos demais. |
| `status` | `Literal['pendente','concluida','cancelada']` | — |

Datas têm precisão de dia, sem horário ou fuso. Não há validação contra o dia
atual. Conclusão posterior ao prazo é válida e representa atraso.

### 1.4 Saída e fórmulas

`ResultadoAnalise` tem exatamente duas chaves: `geral` (`Metricas`) e
`por_prioridade` (dict com `'baixa'`, `'media'` e `'alta'`, cada uma com
`Metricas`).

`Metricas`: `total_tarefas: int`, `total_concluidas: int`,
`total_pendentes: int`, `total_canceladas: int`, `total_atrasadas: int`,
`tempo_medio_dias: float | None`, `percentual_atraso: float | None`.

- **R01.** Totais por status consideram todas as tarefas; concluídas +
  pendentes + canceladas = total.
- **R02.** Só tarefas `'concluida'` entram em duração e atraso.
  `total_atrasadas` não mede pendências vencidas.
- **R03.** Duração = `(data_conclusao - data_inicio).days`. Mesmo dia = 0.
- **R04.** Tempo médio = soma das durações / `total_concluidas`.
- **R05.** Atrasada quando `data_conclusao > prazo`. No prazo não é atraso.
- **R06.** Percentual de atraso = `total_atrasadas / total_concluidas × 100`
  (escala 0–100).
- **R07.** `round(valor, 2)` apenas no resultado final da média e do
  percentual.
- **R08.** Se `total_concluidas == 0`, média e percentual são `None`. Sem
  divisão por zero. Vale para o geral e para cada prioridade.
- **R09.** Lista vazia é válida: totais zero e indicadores `None`, inclusive
  nas três prioridades.
- **R10.** Grupos por prioridade usam as mesmas regras. Resultado
  determinístico, independente da ordem das tarefas.

### 1.5 Validação e exceções

Toda a entrada é validada antes dos cálculos. Ao primeiro erro a análise
termina, sem retorno parcial e sem modificar os dados.

- **`TypeError`:** recipiente que não seja lista; elemento que não seja
  dicionário; campo com tipo incorreto. Ex.: `'Entrada: esperada uma lista de
  tarefas.'` e `'Tarefa 1: campo id deve ser int, sem bool.'`.
- **`TaskValidationError` (subclasse de `ValueError`):** campos
  ausentes/desconhecidos, id não positivo ou repetido, título vazio,
  enumeração inválida, data inexistente ou fora do formato, ordem cronológica
  inválida e inconsistência entre status e conclusão.

Mensagens obrigatórias:

- `'Tarefa 3: a data de conclusão não pode ser anterior à data de início.'`
- `'Tarefa 1: identificador duplicado.'`

Nos demais casos a mensagem identifica o campo e a restrição. Usa o `id` quando
válido; senão, a posição na lista (iniciada em 1). Ordem de validação: pela
ordem da lista; dentro da tarefa — estrutura/chaves, tipos (ordem da 1.3),
valores e duplicidade, formato/calendário, consistência cronológica/status.
Nenhuma tarefa inválida é descartada em silêncio. Zero concluídas é ausência
de dados (`None`), não exceção.

## 2. Cenários de aceite

### 2.1 Cenário 1 — sucesso com prioridades distintas

| | id | titulo | prioridade | inicio | prazo | conclusao | status |
|---|---|---|---|---|---|---|---|
| T1 | 1 | Modelar dados | alta | 2026-09-01 | 2026-09-03 | 2026-09-03 | concluida |
| T2 | 2 | Revisar módulo | alta | 2026-09-01 | 2026-09-04 | 2026-09-05 | concluida |
| T3 | 3 | Escrever resumo | baixa | 2026-09-02 | 2026-09-06 | None | pendente |
| T4 | 4 | Documentar testes | media | 2026-09-02 | 2026-09-05 | 2026-09-03 | concluida |

**Então:**

| Grupo | total | concl. | pend. | canc. | atras. | média | atraso % |
|---|---|---|---|---|---|---|---|
| Geral | 4 | 3 | 1 | 0 | 1 | 2.33 | 33.33 |
| Alta | 2 | 2 | 0 | 0 | 1 | 3.0 | 50.0 |
| Média | 1 | 1 | 0 | 0 | 0 | 1.0 | 0.0 |
| Baixa | 1 | 0 | 1 | 0 | 0 | None | None |

Conferência manual: durações 2, 4 e 1; média 7/3; uma atrasada entre três.

### 2.2 Cenários de exceção

- **C02 (Cenário 2) — Cronologia:** id=3, início `2026-09-05`, prazo
  `2026-09-06`, conclusão `2026-09-03`, concluída → `TaskValidationError` com a
  mensagem obrigatória de conclusão anterior ao início.
- **C03 — Duplicidade:** duas tarefas com id=1 → `'Tarefa 1: identificador
  duplicado.'`.
- **C04 — Calendário:** `data_inicio='2026-02-30'` → erro citando
  `data_inicio` e data inválida.
- **C05 — Tipo:** dicionário no lugar de lista → `TypeError` com `'Entrada:
  esperada uma lista de tarefas.'`.
- **C06 — Status e conclusão:** concluída sem conclusão, ou
  pendente/cancelada com conclusão → erro indicando a inconsistência (um teste
  por variante).

### 2.3 Cenários de borda e integridade

- **C07 — Lista vazia:** quatro conjuntos de métricas com totais zero e
  indicadores `None`.
- **C08 — Sem concluídas:** uma pendente baixa e uma cancelada alta → geral
  total=2, pendentes=1, canceladas=1, concluídas=0, atrasadas=0, indicadores
  `None`; média com total zero.
- **C09 — Mesmo dia:** início, prazo e conclusão `2026-09-03` → média 0.0 e
  atraso 0.0 (zero ≠ `None`).
- **C10 — Limite do prazo:** início `2026-09-01`, prazo e conclusão
  `2026-09-03` → média 2.0, atrasadas 0, percentual 0.0.
- **C11 — Imutabilidade e ordem:** entrada de 2.1 e cópia invertida →
  resultados iguais e entradas intactas.
- **C12 — Validações restantes** (testes separados): id=0, id=True, título só
  com espaços, prioridade e status desconhecidos, campo ausente, campo extra,
  prazo anterior ao início, data `DD/MM/AAAA`.

### 2.4 Test Harness

`tests/test_harness.py` com pytest; fixtures novas por teste;
`pytest.mark.parametrize` para variantes; `pytest.raises` para tipo e
mensagem. Valores esperados calculados à mão.

Rastreabilidade: R01/R02/R04/R06/R07/R10 → 2.1; R03 → C09; R05 → C10 e 2.1;
R08/R09 → C07/C08; validações → C02–C06 e C12; integridade → C11.

Comando: `python -m pytest -q` na raiz do repositório.
