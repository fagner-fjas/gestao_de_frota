"""Interface administrativa do planejamento recorrente (sem automação implícita)."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ConfirmacaoEmbarqueForm, ProgramacaoRecorrenteForm
from .models import ProgramacaoRecorrente, Viagem
from .services.recorrencias import gerar_viagens


class GestorRecorrenciasMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ProgramacaoLista(GestorRecorrenciasMixin, ListView):
    model = ProgramacaoRecorrente
    template_name = 'frota/recorrencias/lista.html'
    paginate_by = 20

    def get_queryset(self):
        return ProgramacaoRecorrente.objects.select_related('rota', 'motorista_padrao', 'veiculo_padrao')


class ProgramacaoDetalhe(GestorRecorrenciasMixin, DetailView):
    model = ProgramacaoRecorrente
    template_name = 'frota/recorrencias/detalhe.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['viagens'] = self.object.viagens.select_related(
            'veiculo', 'motorista'
        ).order_by('-data_programada')[:30]
        hoje = timezone.localdate()
        ctx['inicio_padrao'] = max(hoje, self.object.data_inicio)
        fim = ctx['inicio_padrao'] + timedelta(days=29)
        ctx['fim_padrao'] = min(fim, self.object.data_fim) if self.object.data_fim else fim
        return ctx


class ProgramacaoCriar(GestorRecorrenciasMixin, CreateView):
    model = ProgramacaoRecorrente
    form_class = ProgramacaoRecorrenteForm
    template_name = 'frota/recorrencias/form.html'

    def get_success_url(self):
        messages.success(self.request, 'Programação criada. Gere as viagens no período desejado.')
        return reverse('programacao_detalhe', args=[self.object.pk])


class ProgramacaoEditar(GestorRecorrenciasMixin, UpdateView):
    model = ProgramacaoRecorrente
    form_class = ProgramacaoRecorrenteForm
    template_name = 'frota/recorrencias/form.html'

    def get_success_url(self):
        messages.success(self.request, 'Alterações aplicadas à programação. Viagens já geradas não são modificadas.')
        return reverse('programacao_detalhe', args=[self.object.pk])


@require_POST
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/auth/login/')
def programacao_gerar(request, pk):
    programacao = get_object_or_404(ProgramacaoRecorrente, pk=pk)
    from django import forms

    class PeriodoForm(forms.Form):
        inicio = forms.DateField()
        fim = forms.DateField()

    formulario = PeriodoForm(request.POST)
    if not formulario.is_valid():
        messages.error(request, 'Informe datas válidas para o período de geração.')
    else:
        try:
            resultado = gerar_viagens(
                programacao.pk, formulario.cleaned_data['inicio'], formulario.cleaned_data['fim']
            )
        except ValidationError as erro:
            messages.error(request, '; '.join(erro.messages))
        else:
            messages.success(request,
                             f'Viagens criadas: {resultado.criadas}; já existentes: {resultado.existentes}; '
                             f'não geradas: {len(resultado.recusadas)}.')
            for erro in resultado.recusadas[:5]:
                messages.warning(request, erro)
            if len(resultado.recusadas) > 5:
                messages.warning(request, 'Há outras recusas. Gere um período menor para verificá-las.')
    return redirect('programacao_detalhe', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/auth/login/')
@require_http_methods(['GET', 'POST'])
def confirmar_viagem(request, pk):
    with transaction.atomic():
        viagem = get_object_or_404(
            Viagem.objects.select_for_update().select_related('rota', 'motorista', 'veiculo'), pk=pk
        )
        if not viagem.programacao_recorrente_id:
            raise Http404('A viagem não foi gerada por uma programação recorrente.')
        if viagem.status != Viagem.Status.AGENDADA or viagem.confirmado_em:
            messages.error(request, 'Esta viagem não está disponível para confirmação.')
            return redirect('viagem_detalhe', pk=pk)

        form = ConfirmacaoEmbarqueForm(request.POST or None, viagem=viagem)
        if request.method == 'POST' and form.is_valid():
            viagem.motorista = form.cleaned_data['motorista']
            viagem.veiculo = form.cleaned_data['veiculo']
            viagem.passageiros_embarcados = form.cleaned_data['passageiros_embarcados']
            viagem.confirmado_por = request.user
            viagem.confirmado_em = timezone.now()
            viagem.save(update_fields=[
                'motorista', 'veiculo', 'passageiros_embarcados', 'confirmado_por', 'confirmado_em',
            ])
            messages.success(request, 'Veículo, motorista e contagem confirmados.')
            return redirect('viagem_detalhe', pk=pk)

    return render(request, 'frota/recorrencias/confirmar.html', {
        'viagem': viagem, 'form': form,
    })
