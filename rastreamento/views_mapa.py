"""Endpoints do monitoramento GPS; os dados são restritos a gestores autorizados."""
import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .services.client import TraccarError
from .services.monitoramento import consultar_mapa_frota

logger = logging.getLogger(__name__)


@require_GET
@login_required
@permission_required('rastreamento.view_dispositivogps', raise_exception=True)
def mapa_frota(request):
    return render(request, 'rastreamento/mapa.html')


@never_cache
@require_GET
@login_required
@permission_required('rastreamento.view_dispositivogps', raise_exception=True)
def dados_rastreamento(request):
    try:
        return JsonResponse(consultar_mapa_frota())
    except TraccarError:
        logger.warning('Consulta de monitoramento Traccar indisponível.', exc_info=True)
        return JsonResponse({'erro': 'Não foi possível atualizar as posições GPS.'}, status=503)
