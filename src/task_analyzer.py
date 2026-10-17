"""Módulo TaskAnalyzer: validação de tarefas e cálculo de indicadores.

Implementa o contrato definido em ``specs/task_analyzer_spec.md``. O módulo
recebe uma lista de tarefas, valida toda a entrada antes de qualquer cálculo
e devolve métricas de produtividade gerais e por prioridade.

O processamento ocorre apenas em memória: nada é gravado em arquivo ou banco
de dados e a entrada nunca é modificada.

Interface pública:
    analisar_tarefas: função principal do contrato (seção 1.3 da spec).
    analyze_tasks: alias de ``analisar_tarefas`` exigido pelo enunciado da
        Fase 2.
    TaskValidationError: exceção de validação de valores (subclasse de
        ``ValueError``).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Final, Literal, NoReturn, TypedDict

__all__ = [
    "Tarefa",
    "Metricas",
    "ResultadoAnalise",
    "TaskValidationError",
    "analisar_tarefas",
    "analyze_tasks",
]

logger: Final[logging.Logger] = logging.getLogger(__name__)

Prioridade = Literal["baixa", "media", "alta"]
Status = Literal["pendente", "concluida", "cancelada"]

PRIORIDADES: Final[tuple[str, ...]] = ("baixa", "media", "alta")
STATUS_VALIDOS: Final[tuple[str, ...]] = ("pendente", "concluida", "cancelada")
CAMPOS_OBRIGATORIOS: Final[tuple[str, ...]] = (
    "id",
    "titulo",
    "prioridade",
    "data_inicio",
    "prazo",
    "data_conclusao",
    "status",
)


class Tarefa(TypedDict):
    """Tarefa de entrada, com exatamente os sete campos da seção 1.4.

    Attributes:
        id: Inteiro positivo e único na lista (``bool`` não é aceito).
        titulo: Texto com pelo menos um caractere diferente de espaço.
        prioridade: ``'baixa'``, ``'media'`` ou ``'alta'``.
        data_inicio: Data no formato ``AAAA-MM-DD``.
        prazo: Data no formato ``AAAA-MM-DD``, igual ou posterior ao início.
        data_conclusao: Data ``AAAA-MM-DD`` se concluída; ``None`` nos demais
            status.
        status: ``'pendente'``, ``'concluida'`` ou ``'cancelada'``.
    """

    id: int
    titulo: str
    prioridade: Prioridade
    data_inicio: str
    prazo: str
    data_conclusao: str | None
    status: Status


class Metricas(TypedDict):
    """Indicadores calculados para um conjunto de tarefas (seção 1.5).

    Attributes:
        total_tarefas: Quantidade de tarefas do conjunto.
        total_concluidas: Tarefas com status ``'concluida'``.
        total_pendentes: Tarefas com status ``'pendente'``.
        total_canceladas: Tarefas com status ``'cancelada'``.
        total_atrasadas: Concluídas com conclusão posterior ao prazo.
        tempo_medio_dias: Média de dias corridos até a conclusão, ou ``None``
            se não houver concluídas.
        percentual_atraso: Percentual (0 a 100) de concluídas atrasadas, ou
            ``None`` se não houver concluídas.
    """

    total_tarefas: int
    total_concluidas: int
    total_pendentes: int
    total_canceladas: int
    total_atrasadas: int
    tempo_medio_dias: float | None
    percentual_atraso: float | None


class ResultadoAnalise(TypedDict):
    """Resultado da análise: métricas gerais e por prioridade.

    Attributes:
        geral: Métricas de todas as tarefas.
        por_prioridade: Métricas para ``'baixa'``, ``'media'`` e ``'alta'``.
    """

    geral: Metricas
    por_prioridade: dict[str, Metricas]


class TaskValidationError(ValueError):
    """Erro de validação de valores de uma tarefa.

    Subclasse de ``ValueError``: quem já trata ``ValueError`` (conforme a
    seção 1.6 da especificação) continua funcionando, e quem preferir pode
    tratar especificamente ``TaskValidationError`` (enunciado da Fase 2).
    """


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def _rotulo(tarefa: dict[str, Any], posicao: int) -> str:
    """Monta o identificador usado nas mensagens de erro.

    Usa o ``id`` quando ele já é um inteiro positivo válido; caso contrário,
    usa a posição da tarefa na lista, iniciada em 1.

    Args:
        tarefa: Dicionário da tarefa (possivelmente inválido).
        posicao: Posição da tarefa na lista, iniciada em 1.

    Returns:
        Texto no formato ``'Tarefa <id>'`` ou ``'Tarefa na posição <n>'``.
    """
    identificador = tarefa.get("id")
    if (
        isinstance(identificador, int)
        and not isinstance(identificador, bool)
        and identificador > 0
    ):
        return f"Tarefa {identificador}"
    return f"Tarefa na posição {posicao}"


def _falhar(erro: type[Exception], mensagem: str, campo: str) -> NoReturn:
    """Registra o evento de validação e lança a exceção informada.

    Args:
        erro: Classe da exceção a lançar.
        mensagem: Mensagem que identifica o campo e a restrição.
        campo: Nome do campo inválido, usado apenas no log estruturado.

    Raises:
        Exception: Sempre lança uma instância de ``erro``.
    """
    logger.warning(
        "validacao_falhou",
        extra={"evento": "validacao_falhou", "campo_invalido": campo},
    )
    raise erro(mensagem)


def _validar_estrutura(tarefa: object, posicao: int) -> dict[str, Any]:
    """Confere se o elemento é dicionário e tem exatamente os sete campos.

    Args:
        tarefa: Elemento da lista de entrada.
        posicao: Posição do elemento na lista, iniciada em 1.

    Returns:
        O próprio elemento, já tipado como dicionário.

    Raises:
        TypeError: Se o elemento não for um dicionário.
        TaskValidationError: Se houver campos ausentes ou desconhecidos.
    """
    if not isinstance(tarefa, dict):
        _falhar(
            TypeError,
            f"Tarefa na posição {posicao}: esperado um dicionário.",
            "tarefa",
        )
    rotulo = _rotulo(tarefa, posicao)  # type: ignore[arg-type]
    chaves = set(tarefa)  # type: ignore[arg-type]
    ausentes = [c for c in CAMPOS_OBRIGATORIOS if c not in chaves]
    if ausentes:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo obrigatório ausente: {', '.join(ausentes)}.",
            ausentes[0],
        )
    extras = sorted(str(c) for c in chaves - set(CAMPOS_OBRIGATORIOS))
    if extras:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo desconhecido: {', '.join(extras)}.",
            extras[0],
        )
    return tarefa  # type: ignore[return-value]


def _validar_tipos(tarefa: dict[str, Any], rotulo: str) -> None:
    """Confere o tipo de cada campo, na ordem da seção 1.4.

    Args:
        tarefa: Tarefa com estrutura já validada.
        rotulo: Identificador da tarefa para as mensagens.

    Raises:
        TypeError: Se algum campo tiver tipo incorreto.
    """
    if not isinstance(tarefa["id"], int) or isinstance(tarefa["id"], bool):
        _falhar(TypeError, f"{rotulo}: campo id deve ser int, sem bool.", "id")
    for campo in ("titulo", "prioridade", "data_inicio", "prazo"):
        if not isinstance(tarefa[campo], str):
            _falhar(TypeError, f"{rotulo}: campo {campo} deve ser str.", campo)
    conclusao = tarefa["data_conclusao"]
    if conclusao is not None and not isinstance(conclusao, str):
        _falhar(
            TypeError,
            f"{rotulo}: campo data_conclusao deve ser str ou None.",
            "data_conclusao",
        )
    if not isinstance(tarefa["status"], str):
        _falhar(TypeError, f"{rotulo}: campo status deve ser str.", "status")


def _validar_valores(
    tarefa: dict[str, Any], rotulo: str, ids_vistos: set[int]
) -> None:
    """Confere id positivo, título, enumerações e duplicidade.

    Args:
        tarefa: Tarefa com tipos já validados.
        rotulo: Identificador da tarefa para as mensagens.
        ids_vistos: Ids das tarefas anteriores da lista.

    Raises:
        TaskValidationError: Se algum valor violar o contrato.
    """
    if tarefa["id"] <= 0:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo id deve ser um inteiro positivo.",
            "id",
        )
    if not tarefa["titulo"].strip():
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo titulo não pode ser vazio ou só espaços.",
            "titulo",
        )
    if tarefa["prioridade"] not in PRIORIDADES:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo prioridade deve ser 'baixa', 'media' ou 'alta'.",
            "prioridade",
        )
    if tarefa["status"] not in STATUS_VALIDOS:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo status deve ser 'pendente', 'concluida' "
            "ou 'cancelada'.",
            "status",
        )
    if tarefa["id"] in ids_vistos:
        _falhar(
            TaskValidationError,
            f"Tarefa {tarefa['id']}: identificador duplicado.",
            "id",
        )


def _converter_data(valor: str, campo: str, rotulo: str) -> date:
    """Converte texto ``AAAA-MM-DD`` em ``date``, validando o calendário.

    Args:
        valor: Texto da data.
        campo: Nome do campo, para a mensagem de erro.
        rotulo: Identificador da tarefa para as mensagens.

    Returns:
        A data convertida.

    Raises:
        TaskValidationError: Se o formato for diferente de ``AAAA-MM-DD`` ou
            a data não existir no calendário.
    """
    partes = valor.split("-")
    formato_ok = (
        len(valor) == 10
        and len(partes) == 3
        and [len(p) for p in partes] == [4, 2, 2]
        and all(p.isascii() and p.isdigit() for p in partes)
    )
    if not formato_ok:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo {campo} com data inválida; "
            "use o formato AAAA-MM-DD.",
            campo,
        )
    try:
        return date(int(partes[0]), int(partes[1]), int(partes[2]))
    except ValueError:
        _falhar(
            TaskValidationError,
            f"{rotulo}: campo {campo} com data inválida; "
            "a data não existe no calendário.",
            campo,
        )


def _validar_datas(tarefa: dict[str, Any], rotulo: str) -> None:
    """Confere formato, calendário, cronologia e coerência com o status.

    Args:
        tarefa: Tarefa com valores já validados.
        rotulo: Identificador da tarefa para as mensagens.

    Raises:
        TaskValidationError: Se as datas forem inválidas, fora de ordem ou
            incoerentes com o status.
    """
    inicio = _converter_data(tarefa["data_inicio"], "data_inicio", rotulo)
    prazo = _converter_data(tarefa["prazo"], "prazo", rotulo)
    conclusao_txt = tarefa["data_conclusao"]
    conclusao = (
        None
        if conclusao_txt is None
        else _converter_data(conclusao_txt, "data_conclusao", rotulo)
    )

    if prazo < inicio:
        _falhar(
            TaskValidationError,
            f"{rotulo}: o prazo não pode ser anterior à data de início.",
            "prazo",
        )
    if tarefa["status"] == "concluida":
        if conclusao is None:
            _falhar(
                TaskValidationError,
                f"{rotulo}: tarefa concluída exige data_conclusao preenchida.",
                "data_conclusao",
            )
        if conclusao < inicio:  # type: ignore[operator]
            _falhar(
                TaskValidationError,
                f"{rotulo}: a data de conclusão não pode ser anterior à "
                "data de início.",
                "data_conclusao",
            )
    elif conclusao is not None:
        _falhar(
            TaskValidationError,
            f"{rotulo}: data_conclusao deve ser None quando o status é "
            f"'{tarefa['status']}'.",
            "data_conclusao",
        )


def _validar_entrada(tarefas: object) -> None:
    """Valida toda a entrada, na ordem definida na seção 1.6.

    Args:
        tarefas: Valor recebido pela função pública.

    Raises:
        TypeError: Se a entrada não for lista, um elemento não for dicionário
            ou um campo tiver tipo incorreto.
        TaskValidationError: Para qualquer outra violação do contrato.
    """
    if not isinstance(tarefas, list):
        _falhar(TypeError, "Entrada: esperada uma lista de tarefas.", "entrada")
    ids_vistos: set[int] = set()
    for posicao, item in enumerate(tarefas, start=1):  # type: ignore[arg-type]
        tarefa = _validar_estrutura(item, posicao)
        rotulo = _rotulo(tarefa, posicao)
        _validar_tipos(tarefa, rotulo)
        _validar_valores(tarefa, rotulo, ids_vistos)
        _validar_datas(tarefa, rotulo)
        ids_vistos.add(tarefa["id"])


# ---------------------------------------------------------------------------
# Cálculo e agrupamento
# ---------------------------------------------------------------------------


def _duracao_dias(tarefa: Tarefa) -> int:
    """Calcula a duração em dias corridos de uma tarefa concluída (R03).

    Args:
        tarefa: Tarefa concluída e já validada.

    Returns:
        ``(data_conclusao - data_inicio).days``.
    """
    conclusao = date.fromisoformat(tarefa["data_conclusao"])  # type: ignore[arg-type]
    return (conclusao - date.fromisoformat(tarefa["data_inicio"])).days


def _esta_atrasada(tarefa: Tarefa) -> bool:
    """Indica se a tarefa concluída terminou depois do prazo (R05).

    Args:
        tarefa: Tarefa concluída e já validada.

    Returns:
        ``True`` se ``data_conclusao > prazo``.
    """
    conclusao = date.fromisoformat(tarefa["data_conclusao"])  # type: ignore[arg-type]
    return conclusao > date.fromisoformat(tarefa["prazo"])


def _calcular_metricas(tarefas: list[Tarefa]) -> Metricas:
    """Calcula as métricas de um conjunto de tarefas (R01 a R09).

    Args:
        tarefas: Tarefas já validadas (pode ser vazia).

    Returns:
        Métricas do conjunto; média e percentual são ``None`` quando não há
        tarefas concluídas, sem divisão por zero.
    """
    concluidas = [t for t in tarefas if t["status"] == "concluida"]
    total_concluidas = len(concluidas)
    total_atrasadas = sum(1 for t in concluidas if _esta_atrasada(t))

    tempo_medio: float | None = None
    percentual: float | None = None
    if total_concluidas > 0:
        soma_duracoes = sum(_duracao_dias(t) for t in concluidas)
        tempo_medio = round(soma_duracoes / total_concluidas, 2)
        percentual = round(total_atrasadas / total_concluidas * 100, 2)

    return Metricas(
        total_tarefas=len(tarefas),
        total_concluidas=total_concluidas,
        total_pendentes=sum(1 for t in tarefas if t["status"] == "pendente"),
        total_canceladas=sum(1 for t in tarefas if t["status"] == "cancelada"),
        total_atrasadas=total_atrasadas,
        tempo_medio_dias=tempo_medio,
        percentual_atraso=percentual,
    )


def _agrupar_por_prioridade(tarefas: list[Tarefa]) -> dict[str, list[Tarefa]]:
    """Separa as tarefas nas três prioridades, mesmo as que ficarem vazias.

    Args:
        tarefas: Tarefas já validadas.

    Returns:
        Dicionário com as chaves ``'baixa'``, ``'media'`` e ``'alta'``.
    """
    grupos: dict[str, list[Tarefa]] = {p: [] for p in PRIORIDADES}
    for tarefa in tarefas:
        grupos[tarefa["prioridade"]].append(tarefa)
    return grupos


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------


def analisar_tarefas(tarefas: list[Tarefa]) -> ResultadoAnalise:
    """Valida a lista de tarefas e calcula os indicadores de produtividade.

    Toda a entrada é validada antes dos cálculos. Ao primeiro erro, a função
    termina sem retorno parcial. A lista e os dicionários recebidos não são
    modificados.

    Args:
        tarefas: Lista de tarefas no formato da seção 1.4 da especificação.

    Returns:
        Dicionário com ``geral`` e ``por_prioridade`` (``'baixa'``,
        ``'media'`` e ``'alta'``), cada um com as métricas da seção 1.5.

    Raises:
        TypeError: Se a entrada não for lista, algum elemento não for
            dicionário ou algum campo tiver tipo incorreto.
        TaskValidationError: Se algum valor violar o contrato (campos
            ausentes ou extras, id inválido ou duplicado, título vazio,
            enumeração inválida, data inválida, ordem cronológica inválida ou
            inconsistência entre status e conclusão). É subclasse de
            ``ValueError``.
    """
    _validar_entrada(tarefas)
    logger.info(
        "analise_iniciada",
        extra={"evento": "analise_iniciada", "quantidade_tarefas": len(tarefas)},
    )
    grupos = _agrupar_por_prioridade(tarefas)
    resultado = ResultadoAnalise(
        geral=_calcular_metricas(tarefas),
        por_prioridade={p: _calcular_metricas(grupos[p]) for p in PRIORIDADES},
    )
    logger.info(
        "analise_concluida",
        extra={"evento": "analise_concluida", "quantidade_tarefas": len(tarefas)},
    )
    return resultado


def analyze_tasks(tarefas: list[Tarefa]) -> ResultadoAnalise:
    """Alias de :func:`analisar_tarefas`, com o nome pedido no enunciado.

    Args:
        tarefas: Lista de tarefas no formato da seção 1.4 da especificação.

    Returns:
        O mesmo resultado de :func:`analisar_tarefas`.

    Raises:
        TypeError: Nos mesmos casos de :func:`analisar_tarefas`.
        TaskValidationError: Nos mesmos casos de :func:`analisar_tarefas`.
    """
    return analisar_tarefas(tarefas)
