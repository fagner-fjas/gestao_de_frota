"""Validação comum dos conflitos de alocação em viagens pontuais e recorrentes."""
from datetime import timedelta

from django.db.models import Q

from frota.models import Viagem


def conflitos_de_agenda(partida, rota, veiculo, motorista, passageiros, excluir_id=None):
    """Retorna pares (campo, mensagem) dos recursos sobrepostos no intervalo.

    Considera intervalo semiaberto [início, fim): viagens consecutivas são válidas.
    """
    passageiros = list(passageiros or [])
    filtro = Q()
    if veiculo:
        filtro |= Q(veiculo=veiculo)
    if motorista:
        filtro |= Q(motorista=motorista)
    if passageiros:
        filtro |= Q(passageiros__in=passageiros)
    if not filtro:
        return []

    fim = partida + timedelta(minutes=rota.duracao_minutos)
    outras = (Viagem.objects.filter(
        status__in=[Viagem.Status.AGENDADA, Viagem.Status.EM_ANDAMENTO]
    ).filter(filtro).distinct().select_related('rota').prefetch_related('passageiros'))
    if excluir_id is not None:
        outras = outras.exclude(pk=excluir_id)
    ids = {p.pk for p in passageiros}
    erros = []
    for outra in outras:
        outra_fim = outra.data_hora_partida + timedelta(minutes=outra.rota.duracao_minutos)
        if not (partida < outra_fim and outra.data_hora_partida < fim):
            continue
        referencia = f'viagem #{outra.pk} ({outra})'
        if veiculo and outra.veiculo_id == veiculo.pk:
            erros.append(('veiculo', f'Veículo já alocado na {referencia}.'))
        if motorista and outra.motorista_id == motorista.pk:
            erros.append(('motorista', f'Motorista já alocado na {referencia}.'))
        nomes = [p.nome for p in outra.passageiros.all() if p.pk in ids]
        if nomes:
            erros.append(('passageiros',
                          f'Passageiro(s) já em outra viagem no mesmo período: '
                          f'{", ".join(nomes)} ({referencia}).'))
    return erros
