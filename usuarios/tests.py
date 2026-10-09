from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AutenticacaoTest(TestCase):
    def test_paginas_internas_exigem_login(self):
        for nome in ['plataforma', 'rota_lista', 'motorista_lista', 'veiculo_lista',
                     'passageiro_lista', 'viagem_lista']:
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 302, nome)
            self.assertIn('/auth/login/', resposta.url)

    def test_cadastro_login_e_logout(self):
        r = self.client.post(reverse('cadastro'), {
            'username': 'ana', 'email': 'ana@x.com', 'password': 'senha12345'})
        self.assertRedirects(r, reverse('login'))
        self.assertTrue(User.objects.filter(username='ana').exists())

        r = self.client.post(reverse('login'), {'username': 'ana', 'password': 'senha12345'})
        self.assertRedirects(r, reverse('plataforma'))
        self.assertEqual(self.client.get(reverse('plataforma')).status_code, 200)

        self.client.get(reverse('logout'))
        self.assertEqual(self.client.get(reverse('plataforma')).status_code, 302)

    def test_cadastro_duplicado(self):
        User.objects.create_user('ana', password='senha12345')
        r = self.client.post(reverse('cadastro'), {'username': 'ana', 'password': 'x'})
        self.assertContains(r, 'Já existe um usuário')
        self.assertEqual(User.objects.filter(username='ana').count(), 1)

    def test_login_invalido(self):
        User.objects.create_user('ana', password='senha12345')
        r = self.client.post(reverse('login'), {'username': 'ana', 'password': 'errada'})
        self.assertContains(r, 'Usuário ou senha incorretos.')

    def test_login_volta_para_pagina_pedida(self):
        User.objects.create_user('ana', password='senha12345')
        r = self.client.post('/auth/login/?next=/rotas/', {'username': 'ana', 'password': 'senha12345'})
        self.assertRedirects(r, '/rotas/')
