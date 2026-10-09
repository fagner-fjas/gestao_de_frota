from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as login_django
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


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
    return render(request, 'usuarios/plataforma.html')
