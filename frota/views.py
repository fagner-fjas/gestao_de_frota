from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
<<<<<<< HEAD
from django.db.models import Q
=======
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.dateparse import parse_date
>>>>>>> paineis
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import MotoristaForm, PassageiroForm, RotaForm, VeiculoForm, ViagemForm
from .models import Motorista, Passageiro, Rota, Veiculo, Viagem

def valor_campo(obj, campo):
    display = getattr(obj, f'get_{campo}_display', None)  
    valor = display() if display else getattr(obj, campo)
    if valor is True:
        return 'Sim'
    if valor is False:
        return 'Não'
    if valor is None or valor == '':
        return '—'
    return valor


class ContextoModelo:

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        meta = self.model._meta
        contexto['url_base'] = meta.model_name
        contexto['nome'] = meta.verbose_name
        contexto['nome_plural'] = meta.verbose_name_plural
        return contexto


class ListaBase(LoginRequiredMixin, ContextoModelo, ListView):
    template_name = 'frota/lista.html'
    paginate_by = 20    
    colunas = []        
    campos_busca = []   

    def get_queryset(self):
        queryset = super().get_queryset()
        self.q = self.request.GET.get('q', '').strip()
        if self.q and self.campos_busca:
            filtro = Q()
            for campo in self.campos_busca:
                filtro |= Q(**{f'{campo}__icontains': self.q})
            queryset = queryset.filter(filtro)
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['q'] = self.q
        contexto['status'] = ''
        contexto['cabecalhos'] = [titulo for _, titulo in self.colunas]
        contexto['linhas'] = [
            (obj, [valor_campo(obj, campo) for campo, _ in self.colunas])
            for obj in contexto['object_list']
        ]
        return contexto


class DetalheBase(LoginRequiredMixin, ContextoModelo, DetailView):
    template_name = 'frota/detalhe.html'
    campos_extra = []   

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        obj = self.object
        dados = [
            (campo.verbose_name, valor_campo(obj, campo.name))
            for campo in obj._meta.fields if campo.name != 'id'
        ]
        dados += [(titulo, valor_campo(obj, campo)) for campo, titulo in self.campos_extra]
        contexto['dados'] = dados
        return contexto


class FormularioBase(LoginRequiredMixin, ContextoModelo, SuccessMessageMixin):
    template_name = 'frota/form.html'

    def get_success_url(self):
        return reverse(f'{self.model._meta.model_name}_lista')


class CriarBase(FormularioBase, CreateView):
    success_message = 'Registro criado com sucesso.'


class EditarBase(FormularioBase, UpdateView):
    success_message = 'Registro atualizado com sucesso.'


class ExcluirBase(LoginRequiredMixin, ContextoModelo, DeleteView):
    template_name = 'frota/confirmar_exclusao.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        url_base = self.model._meta.model_name
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                request,
                'Não é possível excluir: existem viagens vinculadas a este registro. '
                'Inative-o pela edição.',
            )
            return redirect(f'{url_base}_detalhe', pk=self.object.pk)
        messages.success(request, 'Registro excluído com sucesso.')
        return redirect(f'{url_base}_lista')


# —————————————————————————————————————————————————————————————————————————————
# Rotas
# —————————————————————————————————————————————————————————————————————————————
class RotaLista(ListaBase):
    model = Rota
    colunas = [('nome', 'Nome'), ('origem', 'Origem'), ('destino', 'Destino'),
               ('distancia_km', 'Distância (km)'), ('ativa', 'Ativa')]
    campos_busca = ['nome', 'origem', 'destino']


class RotaDetalhe(DetalheBase):
    model = Rota


class RotaCriar(CriarBase):
    model = Rota
    form_class = RotaForm


class RotaEditar(EditarBase):
    model = Rota
    form_class = RotaForm


class RotaExcluir(ExcluirBase):
    model = Rota


# —————————————————————————————————————————————————————————————————————————————
# Motoristas
# ————————————————————————————————————————————————————————————————————————————
class MotoristaLista(ListaBase):
    model = Motorista
    colunas = [('nome', 'Nome'), ('cpf', 'CPF'), ('cnh_categoria', 'CNH'),
               ('cnh_validade', 'Validade da CNH'), ('ativo', 'Ativo')]
    campos_busca = ['nome', 'cpf', 'cnh_numero']


class MotoristaDetalhe(DetalheBase):
    model = Motorista


class MotoristaCriar(CriarBase):
    model = Motorista
    form_class = MotoristaForm


class MotoristaEditar(EditarBase):
    model = Motorista
    form_class = MotoristaForm


class MotoristaExcluir(ExcluirBase):
    model = Motorista


# —————————————————————————————————————————————————————————————————————————————
# Veículos
# —————————————————————————————————————————————————————————————————————————————
class VeiculoLista(ListaBase):
    model = Veiculo
    colunas = [('placa', 'Placa'), ('marca', 'Marca'), ('modelo', 'Modelo'),
               ('capacidade', 'Capacidade'), ('situacao', 'Situação')]
    campos_busca = ['placa', 'marca', 'modelo']


class VeiculoDetalhe(DetalheBase):
    model = Veiculo


class VeiculoCriar(CriarBase):
    model = Veiculo
    form_class = VeiculoForm


class VeiculoEditar(EditarBase):
    model = Veiculo
    form_class = VeiculoForm


class VeiculoExcluir(ExcluirBase):
    model = Veiculo


# —————————————————————————————————————————————————————————————————————————————
# Passageiros
# —————————————————————————————————————————————————————————————————————————————
class PassageiroLista(ListaBase):
    model = Passageiro
    colunas = [('nome', 'Nome'), ('documento', 'Documento'),
               ('telefone', 'Telefone'), ('ativo', 'Ativo')]
    campos_busca = ['nome', 'documento']


class PassageiroDetalhe(DetalheBase):
    model = Passageiro


class PassageiroCriar(CriarBase):
    model = Passageiro
    form_class = PassageiroForm


class PassageiroEditar(EditarBase):
    model = Passageiro
    form_class = PassageiroForm


class PassageiroExcluir(ExcluirBase):
    model = Passageiro


# —————————————————————————————————————————————————————————————————————————————
# Viagens (agendamento)
# —————————————————————————————————————————————————————————————————————————————
class ViagemLista(ListaBase):
    model = Viagem
    colunas = [('data_hora_partida', 'Partida'), ('rota', 'Rota'), ('veiculo', 'Veículo'),
               ('motorista', 'Motorista'), ('total_passageiros', 'Passageiros'),
               ('status', 'Status')]
    campos_busca = ['rota__nome', 'veiculo__placa', 'motorista__nome']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('rota', 'veiculo', 'motorista')
        queryset = queryset.prefetch_related('passageiros')
        self.status = self.request.GET.get('status', '')
<<<<<<< HEAD
        if self.status:
            queryset = queryset.filter(status=self.status)
=======
        self.data_filtro = self.request.GET.get('data', '').strip()
        self.pendente = self.request.GET.get('pendente', '') == '1'
        self.rota_filtro = self.request.GET.get('rota', '').strip()
        if self.status in Viagem.Status.values:
            queryset = queryset.filter(status=self.status)
        if self.data_filtro:
            data = parse_date(self.data_filtro)
            if data:
                queryset = queryset.filter(data_hora_partida__date=data)
        if self.rota_filtro.isdecimal():
            queryset = queryset.filter(rota_id=int(self.rota_filtro))
        if self.pendente:
            queryset = queryset.filter(
                programacao_recorrente__isnull=False,
                status=Viagem.Status.AGENDADA,
                confirmado_em__isnull=True,
            )
>>>>>>> paineis
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['status'] = self.status
        contexto['status_choices'] = Viagem.Status.choices
<<<<<<< HEAD
=======
        contexto['data_filtro'] = self.data_filtro
        contexto['rota_filtro'] = self.rota_filtro
        contexto['pendente'] = self.pendente
        contexto['rotas_filtro'] = Rota.objects.filter(ativa=True).order_by('nome')
>>>>>>> paineis
        return contexto


class ViagemDetalhe(DetalheBase):
    model = Viagem
    template_name = 'frota/viagem_detalhe.html'
<<<<<<< HEAD
    campos_extra = [('passageiros_texto', 'Passageiros'),
                    ('total_passageiros', 'Quantidade de passageiros')]
=======
    campos_extra = [('passageiros_texto', 'Passageiros previstos'),
                    ('total_passageiros', 'Quantidade de passageiros previstos')]
>>>>>>> paineis


class ViagemCriar(CriarBase):
    model = Viagem
    form_class = ViagemForm


class ViagemEditar(EditarBase):
    model = Viagem
    form_class = ViagemForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            viagem = self.get_object()
<<<<<<< HEAD
            if viagem.status != Viagem.Status.AGENDADA:
                messages.error(request, 'Somente viagens com status Agendada podem ser editadas.')
=======
            if viagem.programacao_recorrente_id and not request.user.is_staff:
                raise PermissionDenied('Apenas gestores podem alterar viagens recorrentes.')
            if viagem.status != Viagem.Status.AGENDADA or viagem.confirmado_em:
                messages.error(request, 'Somente viagens agendadas e ainda não confirmadas podem ser editadas.')
>>>>>>> paineis
                return redirect('viagem_detalhe', pk=viagem.pk)
        return super().dispatch(request, *args, **kwargs)


class ViagemExcluir(ExcluirBase):
    model = Viagem

<<<<<<< HEAD
=======
    def post(self, request, *args, **kwargs):
        viagem = self.get_object()
        if viagem.programacao_recorrente_id:
            messages.error(request, 'Viagens recorrentes devem ser canceladas, não excluídas. Histórico preservado.')
            return redirect('viagem_detalhe', pk=viagem.pk)
        return super().post(request, *args, **kwargs)


>>>>>>> paineis

TRANSICOES = {
    'iniciar': ([Viagem.Status.AGENDADA], Viagem.Status.EM_ANDAMENTO),
    'concluir': ([Viagem.Status.EM_ANDAMENTO], Viagem.Status.CONCLUIDA),
    'cancelar': ([Viagem.Status.AGENDADA, Viagem.Status.EM_ANDAMENTO], Viagem.Status.CANCELADA),
}


@login_required
@require_POST
def mudar_status(request, pk, acao):
    if acao not in TRANSICOES:
        raise Http404
    viagem = get_object_or_404(Viagem.objects.select_related('veiculo'), pk=pk)
    origens, destino = TRANSICOES[acao]
<<<<<<< HEAD
=======
    if viagem.programacao_recorrente_id and not request.user.is_staff:
        raise PermissionDenied('Apenas gestores podem alterar viagens recorrentes.')
>>>>>>> paineis

    if viagem.status not in origens:
        messages.error(
            request,
            f'Não é possível executar "{acao}" numa viagem {viagem.get_status_display().lower()}.',
        )
        return redirect('viagem_detalhe', pk=pk)

<<<<<<< HEAD
=======
    if (destino == Viagem.Status.EM_ANDAMENTO
            and viagem.programacao_recorrente_id and not viagem.confirmado_em):
        messages.error(request, 'Confirme o motorista, o veículo e o embarque antes de iniciar.')
        return redirect('viagem_detalhe', pk=pk)

>>>>>>> paineis
    veiculo = viagem.veiculo
    if destino == Viagem.Status.EM_ANDAMENTO:
        if veiculo.situacao != Veiculo.Situacao.DISPONIVEL:
            messages.error(request, f'O veículo {veiculo.placa} não está disponível.')
            return redirect('viagem_detalhe', pk=pk)
        veiculo.situacao = Veiculo.Situacao.EM_VIAGEM
    elif viagem.status == Viagem.Status.EM_ANDAMENTO:  
        veiculo.situacao = Veiculo.Situacao.DISPONIVEL

    with transaction.atomic():
        viagem.status = destino
        viagem.save()
        veiculo.save()

    messages.success(request, f'Viagem atualizada: {viagem.get_status_display()}.')
    return redirect('viagem_detalhe', pk=pk)
