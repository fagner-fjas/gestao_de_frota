from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as login_django
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from frota.models import Motorista, Veiculo, Viagem


def cadastro(request):
    if request.method == 'GET':
        return render(request, 'usuarios/cadastro.html')

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')

    if not username or not password:
        messages.error(request, 'Informe o nome de usuário e a senha.')
        return render(request, 'usuarios/cadastro.html')

    if User.objects.filter(username=username).exists():
        messages.error(request, 'Já existe um usuário com esse nome de usuário.')
        return render(request, 'usuarios/cadastro.html')

    User.objects.create_user(username=username, email=email, password=password)
    messages.success(request, 'Usuário cadastrado com sucesso! Faça login.')
    return redirect('login')


def login(request):
    if request.method == 'GET':
        return render(request, 'usuarios/login.html')

    username = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(request, username=username, password=password)

    if user:
        login_django(request, user)
        proximo = request.GET.get('next', '')
        if url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}):
            return redirect(proximo)
        return redirect('plataforma')

    messages.error(request, 'Usuário ou senha incorretos.')
    return render(request, 'usuarios/login.html')


def sair(request):
    logout(request)
    messages.success(request, 'Você saiu do sistema.')
    return redirect('login')


@login_required(login_url='/auth/login/')
def plataforma(request):
    agora = timezone.now()
    hoje = timezone.localdate()

    por_status = dict(
        Viagem.objects.order_by().values_list('status').annotate(total=Count('id'))
    )
    por_situacao = dict(
        Veiculo.objects.order_by().values_list('situacao').annotate(total=Count('id'))
    )

    contexto = {
        'viagens_agendadas': por_status.get(Viagem.Status.AGENDADA, 0),
        'viagens_em_andamento': por_status.get(Viagem.Status.EM_ANDAMENTO, 0),
        'viagens_concluidas': por_status.get(Viagem.Status.CONCLUIDA, 0),
        'veiculos_total': sum(por_situacao.values()),
        'veiculos_disponiveis': por_situacao.get(Veiculo.Situacao.DISPONIVEL, 0),
        'veiculos_manutencao': por_situacao.get(Veiculo.Situacao.MANUTENCAO, 0),
        'motoristas_ativos': Motorista.objects.filter(ativo=True).count(),
        'proximas_viagens': (
            Viagem.objects
            .filter(status=Viagem.Status.AGENDADA, data_hora_partida__gte=agora)
            .select_related('rota', 'veiculo', 'motorista')[:5]
        ),
        'cnh_atencao': (
            Motorista.objects
            .filter(ativo=True, cnh_validade__lte=hoje + timedelta(days=30))
            .order_by('cnh_validade')[:5]
        ),
        'hoje': hoje,
    }
    return render(request, 'usuarios/plataforma.html', contexto)
