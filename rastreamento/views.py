"""Gestão administrativa de GPS: leitura, importação e associação (MVP)."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from rastreamento.forms import AssociacaoGPSForm
from rastreamento.models import DispositivoGPS
from rastreamento.services.associacoes import ConflitoAssociacaoGPS, associar_dispositivo
from rastreamento.services.client import TraccarError
from rastreamento.services.sincronizacao import (
    SincronizacaoGPSInvalida,
    sincronizar_dispositivos,
)

logger = logging.getLogger(__name__)


@login_required
@permission_required('rastreamento.view_dispositivogps', raise_exception=True)
def lista_dispositivos(request):
    dispositivos = DispositivoGPS.objects.select_related('veiculo').order_by('nome', 'pk')
    pagina = Paginator(dispositivos, 20).get_page(request.GET.get('page'))
    return render(request, 'rastreamento/dispositivos.html', {
        'dispositivos': pagina.object_list,
        'page_obj': pagina,
    })


@require_POST
@login_required
@permission_required('rastreamento.add_dispositivogps', raise_exception=True)
def importar_dispositivos(request):
    try:
        resultado = sincronizar_dispositivos()
    except (TraccarError, SincronizacaoGPSInvalida):
        logger.warning('Falha na importação administrativa de GPS.', exc_info=True)
        messages.error(request, 'Não foi possível importar os dispositivos. Confira a conexão e os identificadores no Traccar.')
    else:
        messages.success(
            request,
            f'Importação concluída: {resultado["criados"]} novo(s), '
            f'{resultado["atualizados"]} atualizado(s).',
        )
    return redirect('gps_dispositivos')


@login_required
@permission_required('rastreamento.change_dispositivogps', raise_exception=True)
def editar_associacao(request, pk):
    dispositivo = get_object_or_404(
        DispositivoGPS.objects.select_related('veiculo'), pk=pk
    )
    if request.method == 'POST':
        formulario = AssociacaoGPSForm(request.POST, dispositivo=dispositivo)
        if formulario.is_valid():
            veiculo = formulario.cleaned_data['veiculo']
            try:
                associar_dispositivo(dispositivo.pk, veiculo.pk if veiculo else None)
            except ConflitoAssociacaoGPS as exc:
                formulario.add_error('veiculo', str(exc))
            else:
                messages.success(request, 'Associação GPS atualizada com sucesso.')
                return redirect('gps_dispositivos')
    else:
        formulario = AssociacaoGPSForm(dispositivo=dispositivo)

    return render(request, 'rastreamento/associar.html', {
        'dispositivo': dispositivo,
        'form': formulario,
    })
