"""Test Harness do TaskAnalyzer (Fase 2).

Traduz para pytest os cenários de aceite da especificação
(``specs/task_analyzer_spec.md``, seção 2). Os valores esperados foram
calculados à mão a partir do contrato, sem usar a lógica de produção.

Rastreabilidade (cenário da spec -> teste):
    2.1 (Cenário 1, sucesso)  -> test_cenario_1_*
    C02 (Cenário 2, datas)    -> test_c02_*
    C03 a C06 (exceções)      -> test_c03_* ... test_c06_*
    C07 a C11 (borda)         -> test_c07_* ... test_c11_*
    C12 (validações)          -> test_c12_*

Execução, na raiz do repositório: ``python -m pytest -q``.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import pytest

# Permite rodar tanto "python -m pytest" quanto "pytest" na raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.task_analyzer import (  # noqa: E402
    TaskValidationError,
    analisar_tarefas,
    analyze_tasks,
)

Tarefa = dict[str, Any]


# ---------------------------------------------------------------------------
# Fixtures e auxiliares (dados fictícios, novos a cada teste)
# ---------------------------------------------------------------------------


def _tarefa(**alteracoes: Any) -> Tarefa:
    """Cria uma tarefa concluída válida, aplicando as alterações pedidas."""
    base: Tarefa = {
        "id": 1,
        "titulo": "Tarefa de teste",
        "prioridade": "media",
        "data_inicio": "2026-09-01",
        "prazo": "2026-09-03",
        "data_conclusao": "2026-09-02",
        "status": "concluida",
    }
    base.update(alteracoes)
    return base


def _metricas(
    total: int,
    concluidas: int,
    pendentes: int,
    canceladas: int,
    atrasadas: int,
    media: float | None,
    atraso: float | None,
) -> dict[str, Any]:
    """Monta o dicionário de métricas esperado com as chaves completas."""
    return {
        "total_tarefas": total,
        "total_concluidas": concluidas,
        "total_pendentes": pendentes,
        "total_canceladas": canceladas,
        "total_atrasadas": atrasadas,
        "tempo_medio_dias": media,
        "percentual_atraso": atraso,
    }


VAZIO = _metricas(0, 0, 0, 0, 0, None, None)


@pytest.fixture
def tarefas_cenario_1() -> list[Tarefa]:
    """Quatro tarefas do cenário 2.1 da especificação."""
    return [
        {
            "id": 1,
            "titulo": "Modelar dados",
            "prioridade": "alta",
            "data_inicio": "2026-09-01",
            "prazo": "2026-09-03",
            "data_conclusao": "2026-09-03",
            "status": "concluida",
        },
        {
            "id": 2,
            "titulo": "Revisar módulo",
            "prioridade": "alta",
            "data_inicio": "2026-09-01",
            "prazo": "2026-09-04",
            "data_conclusao": "2026-09-05",
            "status": "concluida",
        },
        {
            "id": 3,
            "titulo": "Escrever resumo",
            "prioridade": "baixa",
            "data_inicio": "2026-09-02",
            "prazo": "2026-09-06",
            "data_conclusao": None,
            "status": "pendente",
        },
        {
            "id": 4,
            "titulo": "Documentar testes",
            "prioridade": "media",
            "data_inicio": "2026-09-02",
            "prazo": "2026-09-05",
            "data_conclusao": "2026-09-03",
            "status": "concluida",
        },
    ]


# ---------------------------------------------------------------------------
# Cenário 1 (2.1) - sucesso com prioridades distintas
# ---------------------------------------------------------------------------


def test_cenario_1_resultado_completo(tarefas_cenario_1: list[Tarefa]) -> None:
    """Durações 2, 4 e 1; média 7/3; uma atrasada entre três concluídas."""
    resultado = analisar_tarefas(tarefas_cenario_1)

    assert resultado == {
        "geral": _metricas(4, 3, 1, 0, 1, 2.33, 33.33),
        "por_prioridade": {
            "baixa": _metricas(1, 0, 1, 0, 0, None, None),
            "media": _metricas(1, 1, 0, 0, 0, 1.0, 0.0),
            "alta": _metricas(2, 2, 0, 0, 1, 3.0, 50.0),
        },
    }


def test_cenario_1_totais_somam_o_total(tarefas_cenario_1: list[Tarefa]) -> None:
    """R01: concluídas + pendentes + canceladas = total, em todos os grupos."""
    resultado = analisar_tarefas(tarefas_cenario_1)
    grupos = [resultado["geral"], *resultado["por_prioridade"].values()]
    for m in grupos:
        soma = m["total_concluidas"] + m["total_pendentes"] + m["total_canceladas"]
        assert soma == m["total_tarefas"]


def test_cenario_1_chaves_exatas(tarefas_cenario_1: list[Tarefa]) -> None:
    """Seção 1.5: saída com exatamente as chaves do contrato."""
    resultado = analisar_tarefas(tarefas_cenario_1)
    assert set(resultado) == {"geral", "por_prioridade"}
    assert set(resultado["por_prioridade"]) == {"baixa", "media", "alta"}
    assert set(resultado["geral"]) == set(VAZIO)


def test_alias_analyze_tasks(tarefas_cenario_1: list[Tarefa]) -> None:
    """O alias pedido no enunciado devolve o mesmo resultado."""
    assert analyze_tasks(tarefas_cenario_1) == analisar_tarefas(tarefas_cenario_1)


# ---------------------------------------------------------------------------
# Cenário 2 (C02) e demais exceções (C03 a C06)
# ---------------------------------------------------------------------------


def test_c02_conclusao_anterior_ao_inicio() -> None:
    """Cenário 2: data_conclusao < data_inicio dispara TaskValidationError."""
    tarefa = _tarefa(
        id=3,
        data_inicio="2026-09-05",
        prazo="2026-09-06",
        data_conclusao="2026-09-03",
    )
    mensagem = "Tarefa 3: a data de conclusão não pode ser anterior à data de início."
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([tarefa])
    assert str(erro.value) == mensagem


def test_c02_excecao_tambem_e_value_error() -> None:
    """TaskValidationError continua sendo ValueError (seção 1.6)."""
    tarefa = _tarefa(id=3, data_inicio="2026-09-05", prazo="2026-09-06",
                     data_conclusao="2026-09-03")
    with pytest.raises(ValueError):
        analisar_tarefas([tarefa])


def test_c03_identificador_duplicado() -> None:
    """C03: duas tarefas válidas com id=1."""
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([_tarefa(id=1), _tarefa(id=1, titulo="Outra")])
    assert str(erro.value) == "Tarefa 1: identificador duplicado."


def test_c04_data_inexistente_no_calendario() -> None:
    """C04: 2026-02-30 não existe."""
    tarefa = _tarefa(data_inicio="2026-02-30")
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([tarefa])
    texto = str(erro.value)
    assert "data_inicio" in texto
    assert "data inválida" in texto


def test_c05_entrada_que_nao_e_lista() -> None:
    """C05: dicionário no lugar da lista."""
    with pytest.raises(TypeError) as erro:
        analisar_tarefas(_tarefa())  # type: ignore[arg-type]
    assert str(erro.value) == "Entrada: esperada uma lista de tarefas."


def test_c06_concluida_sem_data_de_conclusao() -> None:
    """C06 (variante 1): concluída sem data_conclusao."""
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([_tarefa(data_conclusao=None)])
    assert "data_conclusao" in str(erro.value)


@pytest.mark.parametrize("status", ["pendente", "cancelada"])
def test_c06_nao_concluida_com_data_de_conclusao(status: str) -> None:
    """C06 (variantes 2 e 3): pendente/cancelada com conclusão preenchida."""
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([_tarefa(status=status, data_conclusao="2026-09-02")])
    assert "data_conclusao" in str(erro.value)
    assert status in str(erro.value)


# ---------------------------------------------------------------------------
# Casos de borda e integridade (C07 a C11)
# ---------------------------------------------------------------------------


def test_c07_lista_vazia() -> None:
    """C07: lista vazia é válida, totais zero e indicadores None."""
    assert analisar_tarefas([]) == {
        "geral": VAZIO,
        "por_prioridade": {"baixa": VAZIO, "media": VAZIO, "alta": VAZIO},
    }


def test_c08_sem_tarefas_concluidas() -> None:
    """C08: só pendente e cancelada; sem divisão por zero, indicadores None."""
    tarefas = [
        _tarefa(id=1, prioridade="baixa", status="pendente", data_conclusao=None),
        _tarefa(id=2, prioridade="alta", status="cancelada", data_conclusao=None),
    ]
    assert analisar_tarefas(tarefas) == {
        "geral": _metricas(2, 0, 1, 1, 0, None, None),
        "por_prioridade": {
            "baixa": _metricas(1, 0, 1, 0, 0, None, None),
            "media": VAZIO,
            "alta": _metricas(1, 0, 0, 1, 0, None, None),
        },
    }


def test_c09_conclusao_no_mesmo_dia() -> None:
    """C09: zero dias é 0.0, diferente de None."""
    dia = "2026-09-03"
    resultado = analisar_tarefas(
        [_tarefa(data_inicio=dia, prazo=dia, data_conclusao=dia)]
    )
    geral = resultado["geral"]
    assert geral["tempo_medio_dias"] == 0.0
    assert geral["tempo_medio_dias"] is not None
    assert geral["percentual_atraso"] == 0.0
    assert geral["percentual_atraso"] is not None


def test_c10_conclusao_no_limite_do_prazo() -> None:
    """C10: concluir no dia do prazo não é atraso."""
    resultado = analisar_tarefas(
        [_tarefa(data_inicio="2026-09-01", prazo="2026-09-03",
                 data_conclusao="2026-09-03")]
    )
    geral = resultado["geral"]
    assert geral["tempo_medio_dias"] == 2.0
    assert geral["total_atrasadas"] == 0
    assert geral["percentual_atraso"] == 0.0


def test_c11_imutabilidade_e_ordem(tarefas_cenario_1: list[Tarefa]) -> None:
    """C11: ordem não altera o resultado e a entrada não é modificada."""
    invertida = list(reversed(copy.deepcopy(tarefas_cenario_1)))
    original_antes = copy.deepcopy(tarefas_cenario_1)
    invertida_antes = copy.deepcopy(invertida)

    assert analisar_tarefas(tarefas_cenario_1) == analisar_tarefas(invertida)
    assert tarefas_cenario_1 == original_antes
    assert invertida == invertida_antes


# ---------------------------------------------------------------------------
# C12 - validações restantes (um defeito por teste)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("alteracoes", "trecho"),
    [
        pytest.param({"id": 0}, "id", id="id_zero"),
        pytest.param({"titulo": "   "}, "titulo", id="titulo_so_espacos"),
        pytest.param({"prioridade": "urgente"}, "prioridade", id="prioridade_invalida"),
        pytest.param({"status": "arquivada"}, "status", id="status_invalido"),
        pytest.param({"prazo": "2026-08-31"}, "prazo", id="prazo_antes_do_inicio"),
        pytest.param({"data_inicio": "01/09/2026"}, "data_inicio", id="formato_dd_mm_aaaa"),
    ],
)
def test_c12_valores_invalidos(alteracoes: dict[str, Any], trecho: str) -> None:
    """C12: valores inválidos geram TaskValidationError citando o campo."""
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([_tarefa(**alteracoes)])
    assert trecho in str(erro.value)


def test_c12_id_bool_e_type_error() -> None:
    """C12: id=True não é aceito como inteiro."""
    with pytest.raises(TypeError) as erro:
        analisar_tarefas([_tarefa(id=True)])
    assert "id deve ser int, sem bool" in str(erro.value)


def test_c12_campo_ausente() -> None:
    """C12: falta o campo prazo."""
    tarefa = _tarefa()
    del tarefa["prazo"]
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([tarefa])
    assert "prazo" in str(erro.value)


def test_c12_campo_extra() -> None:
    """C12: campo desconhecido é rejeitado."""
    with pytest.raises(TaskValidationError) as erro:
        analisar_tarefas([_tarefa(responsavel="Fulano")])
    assert "responsavel" in str(erro.value)


def test_c12_elemento_que_nao_e_dicionario() -> None:
    """Seção 1.6: elemento da lista que não é dicionário gera TypeError."""
    with pytest.raises(TypeError) as erro:
        analisar_tarefas(["não sou uma tarefa"])  # type: ignore[list-item]
    assert "posição 1" in str(erro.value)
