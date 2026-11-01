from django.contrib.auth.models import Permission, User
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



class PlataformaRastreamentoTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('gestor', password='senha12345')

    def test_plataforma_sem_permissao_gps_nao_renderiza_widget(self):
        self.client.login(username='gestor', password='senha12345')
        resposta = self.client.get(reverse('plataforma'))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'id="resumo-gps"')
        self.assertNotContains(resposta, reverse('rastreamento_dados'))

    def test_plataforma_com_permissao_gps_renderiza_widget_e_links(self):
        permissao = Permission.objects.get(
            content_type__app_label='rastreamento', codename='view_dispositivogps'
        )
        self.usuario.user_permissions.add(permissao)
        self.client.login(username='gestor', password='senha12345')
        resposta = self.client.get(reverse('plataforma'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Rastreamento GPS')
        self.assertContains(resposta, reverse('rastreamento_dados'))
        self.assertContains(resposta, reverse('gps_dispositivos'))
        self.assertContains(resposta, reverse('rastreamento'))
        self.assertContains(resposta, 'Dispositivos GPS')
        self.assertContains(resposta, 'Mapa da Frota')

    def test_painel_mostra_operacao_antes_do_mapa_gps(self):
        permissao = Permission.objects.get(
            content_type__app_label='rastreamento', codename='view_dispositivogps'
        )
        self.usuario.user_permissions.add(permissao)
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('plataforma'))
        conteudo = resposta.content.decode()
        self.assertLess(conteudo.index('Próximas viagens'), conteudo.index('id="resumo-gps"'))
        self.assertLess(conteudo.index('Situação operacional'), conteudo.index('id="resumo-gps"'))

    def test_painel_tem_atalhos_para_cadastros(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('plataforma'))
        self.assertContains(resposta, reverse('viagem_nova'))
        self.assertContains(resposta, reverse('veiculo_nova'))
        self.assertContains(resposta, reverse('rota_nova'))
        self.assertContains(resposta, reverse('motorista_nova'))

    def test_painel_sem_gps_mantem_operacao_geral(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('plataforma'))
        self.assertContains(resposta, 'Situação operacional')
        self.assertContains(resposta, 'Próximas viagens')
        self.assertNotContains(resposta, 'painel-gps-widget')
