"""Geração explícita e idempotente de ocorrências de viagens recorrentes.

Não há tarefa agendada nem dependência adicional. A execução é invocada pela
interface administrativa ou por comando de gestão, quando autorizado.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from frota.models import ProgramacaoRecorrente, Veiculo, Viagem
from frota.services.agenda import conflitos_de_agenda


@dataclass
class ResultadoGeracao:
    criadas: int = 0
    existentes: int = 0
    recusadas: list[str] = field(default_factory=list)


def gerar_viagens(programacao_id, inicio, fim):
    """Materializa no máximo 31 datas, preservando alterações em ocorrências existentes.

    Geração idempotente por (programação, data); em disputa concorrente, o lock
    da programação serializa as operações no MySQL. A constraint é a defesa final.
    """
    hoje = timezone.localdate()
    if inicio > fim:
        raise ValidationError('A data inicial deve ser anterior ou igual à final.')
    if inicio < hoje:
        raise ValidationError('Não é permitido gerar viagens com datas anteriores a hoje.')
    if (fim - inicio).days > 30:
        raise ValidationError('Gere no máximo 31 dias por operação.')

    resultado = ResultadoGeracao()
    with transaction.atomic():
        programacao = (ProgramacaoRecorrente.objects.select_for_update()
                       .select_related('rota', 'motorista_padrao', 'veiculo_padrao')
                       .get(pk=programacao_id))
        if not programacao.ativa:
            raise ValidationError('A programação está inativa.')
        if inicio < programacao.data_inicio or (
            programacao.data_fim and fim > programacao.data_fim
        ):
            raise ValidationError('O período deve estar dentro da vigência da programação.')

        dias = {int(d) for d in programacao.dias_semana.split(',') if d}
        if not dias or not dias.issubset(set(range(7))):
            raise ValidationError('Os dias da programação são inválidos.')
        passageiros = list(programacao.passageiros.filter(ativo=True))
        if len(passageiros) != programacao.passageiros.count():
            raise ValidationError('Há passageiros inativos vinculados à programação.')
        if not passageiros:
            raise ValidationError('Associe pelo menos um passageiro antes de gerar viagens.')
        if len(passageiros) > programacao.veiculo_padrao.capacidade:
            raise ValidationError('A quantidade de passageiros excede a capacidade do veículo.')
        if not programacao.rota.ativa or not programacao.motorista_padrao.ativo:
            raise ValidationError('Rota ou motorista padrão inativo.')
        if programacao.veiculo_padrao.situacao != Veiculo.Situacao.DISPONIVEL:
            raise ValidationError('Veículo padrão indisponível para o planejamento.')

        atual = inicio
        while atual <= fim:
            if atual.weekday() not in dias:
                atual += timedelta(days=1)
                continue
            if Viagem.objects.filter(
                programacao_recorrente=programacao, data_programada=atual
            ).exists():
                resultado.existentes += 1
                atual += timedelta(days=1)
                continue
            if programacao.motorista_padrao.cnh_validade < atual:
                resultado.recusadas.append(f'{atual:%d/%m/%Y}: CNH vencida.')
                atual += timedelta(days=1)
                continue

            partida = timezone.make_aware(
                datetime.combine(atual, programacao.hora_partida),
                timezone.get_current_timezone(),
            )
            conflitos = conflitos_de_agenda(
                partida, programacao.rota, programacao.veiculo_padrao,
                programacao.motorista_padrao, passageiros,
            )
            if conflitos:
                resultado.recusadas.append(
                    f'{atual:%d/%m/%Y}: {conflitos[0][1]}'
                )
                atual += timedelta(days=1)
                continue
            viagem = Viagem.objects.create(
                programacao_recorrente=programacao,
                data_programada=atual,
                data_hora_partida=partida,
                rota=programacao.rota,
                veiculo=programacao.veiculo_padrao,
                motorista=programacao.motorista_padrao,
            )
            viagem.passageiros.set(passageiros)
            resultado.criadas += 1
            atual += timedelta(days=1)
    return resultado
