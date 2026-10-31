import logging

from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from .models import Veiculo
from .services.traccar import (
    TraccarError,
    listar_dispositivos,
    ultimas_posicoes,
)

logger = logging.getLogger(__name__)


@login_required
@permission_required(
    "frota.view_veiculo",
    raise_exception=True,
)
def mapa_frota(request):
    return render(
        request,
        "frota/rastreamento.html",
    )


@never_cache
@login_required
@permission_required(
    "frota.view_veiculo",
    raise_exception=True,
)
def dados_rastreamento(request):
    try:
        dispositivos = {
            item["id"]: item
            for item in listar_dispositivos()
        }

        posicoes = {
            item["deviceId"]: item
            for item in ultimas_posicoes()
        }

    except TraccarError:
        logger.exception(
            "Falha ao consultar posições do Traccar"
        )
        return JsonResponse(
            {"erro": "Rastreamento indisponível."},
            status=503,
        )

    veiculos = Veiculo.objects.filter(
        traccar_device_id__isnull=False
    )

    resultado = []

    for veiculo in veiculos:
        device_id = veiculo.traccar_device_id
        dispositivo = dispositivos.get(device_id)
        posicao = posicoes.get(device_id)

        if not dispositivo or not posicao:
            continue

        resultado.append({
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": veiculo.modelo,
            "latitude": posicao["latitude"],
            "longitude": posicao["longitude"],
            "horario": posicao.get("fixTime"),
            "status": dispositivo.get(
                "status", "unknown"
            ),
        })

    return JsonResponse({
        "veiculos": resultado
    })