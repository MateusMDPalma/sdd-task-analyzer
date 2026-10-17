# sdd-task-analyzer

Módulo Python que valida uma lista de tarefas e calcula indicadores de
produtividade (tempo médio de conclusão, percentual de atraso e totais por
situação), no geral e por prioridade. Projeto do Bootcamp III (CEUB),
desenvolvido com **Spec-Driven Development (SDD)**: a especificação vem primeiro,
os testes traduzem os cenários de aceite e o código é gerado por IA e homologado
por humano.

**Autor:** Mateus de Miranda Palma Dias

## Status do build

| Item | Status |
|---|---|
| Fase 1 — Especificação SDD | Concluída |
| Fase 2 — Implementação com IA + Test Harness | 27 testes, 100% aprovados (`python -m pytest -q`) |
| Fase 3 — CI/CD, Docker e relatório de governança | Planejada |

## Estrutura

```
sdd-task-analyzer/
├── README.md               # Este arquivo
├── CONTEXT_RULES.md        # Regras de governança para a IA
├── .gitignore
├── requirements.txt        # Dependência de desenvolvimento (pytest)
├── specs/
│   └── task_analyzer_spec.md   # Contrato SDD (v1.1)
├── tests/
│   └── test_harness.py     # Suíte pytest (cenários 2.1 e C02–C12)
└── src/
    └── task_analyzer.py    # Código gerado via IA e homologado
```

## Requisitos

- Python 3.11 ou superior
- pytest (apenas para os testes)

## Instalação e testes

```bash
git clone https://github.com/<seu-usuario>/sdd-task-analyzer.git
cd sdd-task-analyzer
python -m venv venv
# Windows: venv\Scripts\activate   |   Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m pytest -v
```

## Uso

```python
from src.task_analyzer import analisar_tarefas, TaskValidationError

tarefas = [
    {
        "id": 1,
        "titulo": "Modelar dados",
        "prioridade": "alta",
        "data_inicio": "2026-09-01",
        "prazo": "2026-09-03",
        "data_conclusao": "2026-09-03",
        "status": "concluida",
    },
]

try:
    resultado = analisar_tarefas(tarefas)   # ou analyze_tasks(tarefas)
    print(resultado["geral"]["tempo_medio_dias"])  # 2.0
except (TypeError, TaskValidationError) as erro:
    print(f"Entrada inválida: {erro}")
```

## Decisões de contrato

- `analyze_tasks` e `TaskValidationError` foram incluídos na Fase 2 para atender
  ao enunciado. `TaskValidationError` herda de `ValueError`, então nada da
  especificação da Fase 1 mudou.
- Sem tarefas concluídas, `tempo_medio_dias` e `percentual_atraso` são `None`
  (ausência de dados), e não `0.0`. Isso evita divisão por zero sem confundir
  "não há dados" com "zero dias". Ver `specs/task_analyzer_spec.md`, R08 e C09.

## Limitações

- Processamento apenas em memória; sem persistência, interface ou integrações.
- Datas com precisão de dia, sem horário ou fuso.
- `total_atrasadas` conta só tarefas concluídas após o prazo; pendências
  vencidas não entram.

## Fluxo de versionamento

`main` recebe apenas código revisado. O trabalho é feito em branches
`feature/*` e integrado por Pull Request após os testes e a revisão humana
contra o `CONTEXT_RULES.md`.
