"""Entrega 4: casos de uso e HTTP do monitoramento GPS sem Traccar real."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from frota.models import Veiculo
from rastreamento.models import DispositivoGPS
from rastreamento.services.client import TraccarUnavailableError
from rastreamento.services.monitoramento import consultar_mapa_frota


class MapaFrotaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.veiculo = Veiculo.objects.create(
            placa='ABC1D23', marca='Teste', modelo='Kombi', ano=2024,
            tipo=Veiculo.Tipo.ONIBUS, capacidade=25,
        )
        cls.gps = DispositivoGPS.objects.create(
            nome='Rastreador da Kombi', traccar_id=19,
            unique_id='GPS-19', veiculo=cls.veiculo,
        )
        cls.usuario = get_user_model().objects.create_user(
            username='gestor-mapa', password='senha-de-teste',
        )
        permissao = Permission.objects.get(
            content_type__app_label='rastreamento', codename='view_dispositivogps',
        )
        cls.usuario.user_permissions.add(permissao)

    def dados_remotos(self, horario=None):
        return (
            [{'id': 19, 'name': 'GPS', 'status': 'online'}],
            [{
                'deviceId': 19, 'latitude': -7.67, 'longitude': -36.88,
                'fixTime': (horario or timezone.now()).isoformat(),
                'speed': 10,
                'attributes': {'batteryLevel': 72},
            }],
        )

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_consulta_mapa_com_posicao_recente(self, dispositivos, posicoes):
        dispositivos.return_value, posicoes.return_value = self.dados_remotos()
        dados = consultar_mapa_frota()
        self.assertEqual(dados['resumo']['total_vinculados'], 1)
        self.assertEqual(dados['resumo']['recentes'], 1)
        veiculo = dados['veiculos'][0]
        self.assertEqual(veiculo['id'], self.veiculo.id)
        self.assertEqual(veiculo['estado_localizacao'], 'recente')
        self.assertEqual(veiculo['velocidade_kmh'], 18.5)
        self.assertEqual(veiculo['bateria'], 72)
        self.assertEqual(veiculo['status_dispositivo'], 'online')

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_posicao_antiga_nao_e_marcada_como_recente(self, dispositivos, posicoes):
        dispositivos.return_value, posicoes.return_value = self.dados_remotos(
            timezone.now() - timedelta(minutes=12)
        )
        resultado = consultar_mapa_frota()
        self.assertEqual(resultado['resumo']['desatualizadas'], 1)
        self.assertEqual(resultado['resumo']['recentes'], 0)
        self.assertEqual(resultado['veiculos'][0]['estado_localizacao'], 'desatualizada')

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_posicao_atrasada(self, dispositivos, posicoes):
        dispositivos.return_value, posicoes.return_value = self.dados_remotos(
            timezone.now() - timedelta(seconds=120)
        )
        resultado = consultar_mapa_frota()
        self.assertEqual(resultado['resumo']['atrasadas'], 1)
        self.assertEqual(resultado['veiculos'][0]['estado_localizacao'], 'atrasada')

    @patch('rastreamento.services.monitoramento.ultimas_posicoes', return_value=[])
    @patch('rastreamento.services.monitoramento.listar_dispositivos', return_value=[{'id': 19, 'status': 'offline'}])
    def test_veiculo_sem_posicao_permanece_no_resultado(self, dispositivos, posicoes):
        dados = consultar_mapa_frota()
        self.assertEqual(dados['resumo']['sem_posicao'], 1)
        self.assertEqual(len(dados['veiculos']), 1)
        self.assertIsNone(dados['veiculos'][0]['latitude'])
        self.assertEqual(dados['veiculos'][0]['status_dispositivo'], 'offline')

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_data_ausente_ou_futura_nao_e_recente(self, dispositivos, posicoes):
        dispositivos.return_value, posicoes.return_value = self.dados_remotos()
        posicoes.return_value[0].pop('fixTime')
        self.assertEqual(consultar_mapa_frota()['veiculos'][0]['estado_localizacao'], 'sem_horario')
        posicoes.return_value[0]['fixTime'] = (timezone.now() + timedelta(hours=2)).isoformat()
        self.assertEqual(consultar_mapa_frota()['veiculos'][0]['estado_localizacao'], 'sem_horario')

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_filtra_nao_associados_e_inativos(self, dispositivos, posicoes):
        DispositivoGPS.objects.create(nome='Sem vínculo', traccar_id=20)
        outro = Veiculo.objects.create(
            placa='DEF2G34', marca='Teste', modelo='Van', ano=2024,
            tipo=Veiculo.Tipo.VAN, capacidade=12,
        )
        DispositivoGPS.objects.create(nome='Inativo', traccar_id=21, veiculo=outro, ativo=False)
        dispositivos.return_value, posicoes.return_value = self.dados_remotos()
        dados = consultar_mapa_frota()
        self.assertEqual([v['traccar_id'] for v in dados['veiculos']], [19])
        self.assertEqual(dados['resumo']['total_vinculados'], 1)

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_nao_ler_campo_legado_para_gerar_o_mapa(self, dispositivos, posicoes):
        self.veiculo.traccar_device_id = 999
        self.veiculo.save(update_fields=['traccar_device_id'])
        dispositivos.return_value, posicoes.return_value = self.dados_remotos()
        self.assertEqual(consultar_mapa_frota()['veiculos'][0]['traccar_id'], 19)

    @patch('rastreamento.services.monitoramento.ultimas_posicoes')
    @patch('rastreamento.services.monitoramento.listar_dispositivos')
    def test_velocidade_e_bateria_invalidas_sao_omitidas(self, dispositivos, posicoes):
        dispositivos.return_value, posicoes.return_value = self.dados_remotos()
        posicoes.return_value[0]['speed'] = -5
        posicoes.return_value[0]['attributes']['batteryLevel'] = 200
        dados = consultar_mapa_frota()
        self.assertIsNone(dados['veiculos'][0]['velocidade_kmh'])
        self.assertIsNone(dados['veiculos'][0]['bateria'])

    def test_nao_consulta_traccar_quando_nao_ha_associacoes(self):
        self.gps.veiculo = None
        self.gps.save()
        with patch('rastreamento.services.monitoramento.listar_dispositivos') as dispositivos:
            dados = consultar_mapa_frota()
        self.assertEqual(dados['veiculos'], [])
        dispositivos.assert_not_called()

    def test_autenticacao_e_permissao_nas_duas_urls(self):
        for nome in ('rastreamento', 'rastreamento_dados'):
            with self.subTest(nome=nome):
                url = reverse(nome)
                self.assertEqual(self.client.get(url).status_code, 302)
                comum = get_user_model().objects.create_user(
                    username='comum-' + nome, password='senha-de-teste'
                )
                self.client.force_login(comum)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.client.logout()

    def test_ver_veiculos_nao_autoriza_rastreamento(self):
        usuario = get_user_model().objects.create_user(
            username='veiculos-sem-gps', password='senha-de-teste',
        )
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='frota', codename='view_veiculo',
        ))
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse('rastreamento')).status_code, 403)
        self.assertEqual(self.client.get(reverse('rastreamento_dados')).status_code, 403)

    def test_mapa_usa_template_tailadmin(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('rastreamento'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'base.html')
        self.assertTemplateUsed(resposta, 'rastreamento/mapa.html')

    @patch('rastreamento.views_mapa.consultar_mapa_frota')
    def test_endpoint_json_e_sem_cache(self, consultar):
        consultar.return_value = {'veiculos': [], 'resumo': {'total_vinculados': 0}, 'consultado_em': '2026-10-31T12:00:00+00:00'}
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('rastreamento_dados'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), consultar.return_value)
        self.assertIn('no-store', resposta['Cache-Control'])

    @patch('rastreamento.views_mapa.consultar_mapa_frota', side_effect=TraccarUnavailableError())
    def test_falha_traccar_retorna_503_sem_posicao_falsa(self, consultar):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('rastreamento_dados'))
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn('veiculos', resposta.json())

    def test_apenas_get_e_permitido(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post(reverse('rastreamento')).status_code, 405)
        self.assertEqual(self.client.post(reverse('rastreamento_dados')).status_code, 405)
