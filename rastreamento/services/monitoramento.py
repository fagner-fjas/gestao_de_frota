from datetime import timezone as dt_timezone
from math import isfinite

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rastreamento.models import DispositivoGPS
from .dispositivos import listar_dispositivos
from .localizacao import ultimas_posicoes

LIMITE_RECENTE_SEGUNDOS = 90
LIMITE_ATRASADA_SEGUNDOS = 180
TOLERANCIA_FUTURO_SEGUNDOS = 60


def _numero_aceitavel(valor, minimo=None, maximo=None):
    if type(valor) not in (int, float) or not isfinite(valor):
        return None
    if minimo is not None and valor < minimo:
        return None
    if maximo is not None and valor > maximo:
        return None
    return float(valor)


def _idade_posicao(horario, agora):
    if not isinstance(horario, str):
        return None
    try:
        instante = parse_datetime(horario)
    except (ValueError, TypeError):
        return None
    if instante is None:
        return None
    if timezone.is_naive(instante):
        instante = instante.replace(tzinfo=dt_timezone.utc)
    idade = (agora - instante).total_seconds()
    if idade < -TOLERANCIA_FUTURO_SEGUNDOS:
        return None
    return max(0, int(idade))


def _estado_localizacao(posicao, agora):
    if posicao is None:
        return 'sem_posicao', None
    idade = _idade_posicao(posicao.get('fixTime'), agora)
    if idade is None:
        return 'sem_horario', None
    if idade <= LIMITE_RECENTE_SEGUNDOS:
        return 'recente', idade
    if idade <= LIMITE_ATRASADA_SEGUNDOS:
        return 'atrasada', idade
    return 'desatualizada', idade


def consultar_mapa_frota():
    gps_vinculados = list(
        DispositivoGPS.objects.filter(ativo=True, veiculo__isnull=False)
        .select_related('veiculo')
        .order_by('veiculo__placa', 'pk')
    )

    if gps_vinculados:
        dispositivos = {item['id']: item for item in listar_dispositivos()}
        posicoes = {item['deviceId']: item for item in ultimas_posicoes()}
    else:
        dispositivos, posicoes = {}, {}

    agora = timezone.now()
    veiculos = []
    contadores = {
        'total_vinculados': len(gps_vinculados),
        'com_posicao': 0,
        'recentes': 0,
        'atrasadas': 0,
        'desatualizadas': 0,
        'sem_horario': 0,
        'sem_posicao': 0,
    }

    for gps in gps_vinculados:
        dispositivo = dispositivos.get(gps.traccar_id) or {}
        posicao = posicoes.get(gps.traccar_id)
        estado, idade = _estado_localizacao(posicao, agora)
        contadores[{
            'recente': 'recentes',
            'atrasada': 'atrasadas',
            'desatualizada': 'desatualizadas',
            'sem_horario': 'sem_horario',
            'sem_posicao': 'sem_posicao',
        }[estado]] += 1
        if posicao is not None:
            contadores['com_posicao'] += 1

        atributos = (posicao or {}).get('attributes') or {}
        if not isinstance(atributos, dict):
            atributos = {}
        bateria = _numero_aceitavel(atributos.get('batteryLevel'), 0, 100)
        velocidade_nos = _numero_aceitavel((posicao or {}).get('speed'), 0)
        status = dispositivo.get('status')
        if status not in ('online', 'offline', 'unknown'):
            status = 'unknown'

        veiculos.append({
            'id': gps.veiculo_id,
            'placa': gps.veiculo.placa,
            'modelo': gps.veiculo.modelo,
            'gps_nome': gps.nome,
            'traccar_id': gps.traccar_id,
            'latitude': posicao['latitude'] if posicao is not None else None,
            'longitude': posicao['longitude'] if posicao is not None else None,
            'horario': (posicao or {}).get('fixTime'),
            'idade_segundos': idade,
            'estado_localizacao': estado,
            'status_dispositivo': status,
            'velocidade_kmh': round(velocidade_nos * 1.852, 1) if velocidade_nos is not None else None,
            'bateria': bateria,
        })

    return {'veiculos': veiculos, 'resumo': contadores, 'consultado_em': agora.isoformat()}
