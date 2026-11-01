"""Entrega 3: sincronização, associações, acesso e regressão do legado."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from frota.forms import VeiculoForm
from frota.models import Veiculo
from rastreamento.models import DispositivoGPS
from rastreamento.services.associacoes import ConflitoAssociacaoGPS, associar_dispositivo
from rastreamento.services.client import TraccarResponseError
from rastreamento.services.sincronizacao import (
    SincronizacaoGPSInvalida,
    sincronizar_dispositivos,
)


class UtilitariosGPS:
    @staticmethod
    def veiculo(placa):
        return Veiculo.objects.create(
            placa=placa, marca='Teste', modelo='Ônibus', ano=2024,
            tipo=Veiculo.Tipo.ONIBUS, capacidade=30,
        )

    @staticmethod
    def dados(id=101, unique_id='GPS-101', nome='GPS 101'):
        return {'id': id, 'uniqueId': unique_id, 'name': nome}


class SincronizacaoTestes(UtilitariosGPS, TestCase):
    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_importacao_idempotente(self, listar):
        listar.return_value = [self.dados()]
        self.assertEqual(sincronizar_dispositivos(), {'criados': 1, 'atualizados': 0})
        self.assertEqual(sincronizar_dispositivos(), {'criados': 0, 'atualizados': 0})
        self.assertEqual(DispositivoGPS.objects.count(), 1)
        self.assertEqual(DispositivoGPS.objects.get().unique_id, 'GPS-101')

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_preserva_nome_customizado_vinculo_e_status(self, listar):
        veiculo = self.veiculo('ABC1D23')
        gps = DispositivoGPS.objects.create(
            nome='Nome administrativo', traccar_id=101,
            unique_id='GPS-101', ativo=False, veiculo=veiculo,
        )
        listar.return_value = [self.dados(nome='Nome remoto alterado')]
        sincronizar_dispositivos()
        gps.refresh_from_db()
        self.assertEqual(gps.nome, 'Nome administrativo')
        self.assertEqual(gps.veiculo, veiculo)
        self.assertFalse(gps.ativo)

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_completa_identificador_de_dispositivo_migrado(self, listar):
        gps = DispositivoGPS.objects.create(
            nome='GPS Traccar #101 (migrado)', traccar_id=101,
        )
        listar.return_value = [self.dados(nome='Ônibus 01')]
        self.assertEqual(sincronizar_dispositivos()['atualizados'], 1)
        gps.refresh_from_db()
        self.assertEqual(gps.nome, 'Ônibus 01')
        self.assertEqual(gps.unique_id, 'GPS-101')

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_identidade_alterada_nao_e_aceita(self, listar):
        DispositivoGPS.objects.create(nome='GPS', traccar_id=101, unique_id='ORIGINAL')
        listar.return_value = [self.dados(unique_id='OUTRO')]
        with self.assertRaises(SincronizacaoGPSInvalida):
            sincronizar_dispositivos()
        self.assertEqual(DispositivoGPS.objects.get().unique_id, 'ORIGINAL')

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_falha_no_meio_da_importacao_desfaz_tudo(self, listar):
        DispositivoGPS.objects.create(nome='GPS existente', traccar_id=102, unique_id='GPS-102')
        listar.return_value = [self.dados(), self.dados(102, 'GPS-ALTERADO', 'Conflito')]
        with self.assertRaises(SincronizacaoGPSInvalida):
            sincronizar_dispositivos()
        self.assertFalse(DispositivoGPS.objects.filter(traccar_id=101).exists())

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_payload_invalido_nao_modifica_o_banco(self, listar):
        listar.return_value = [self.dados(), {'id': 102, 'name': 'Sem uniqueId'}]
        with self.assertRaises(TraccarResponseError) as erro:
            sincronizar_dispositivos()
        self.assertIn('identificação', str(erro.exception))
        self.assertEqual(DispositivoGPS.objects.count(), 0)

    @patch('rastreamento.services.sincronizacao.listar_dispositivos')
    def test_gps_ausente_do_traccar_nao_e_excluido(self, listar):
        DispositivoGPS.objects.create(nome='GPS local', traccar_id=201)
        listar.return_value = []
        sincronizar_dispositivos()
        self.assertTrue(DispositivoGPS.objects.filter(traccar_id=201).exists())


class AssociacoesTestes(UtilitariosGPS, TestCase):
    def setUp(self):
        self.v1 = self.veiculo('ABC1D23')
        self.v2 = self.veiculo('ABC2D34')
        self.gps = DispositivoGPS.objects.create(nome='GPS 1', traccar_id=55)

    def test_vincular_atualiza_o_mapa_legado(self):
        associar_dispositivo(self.gps.pk, self.v1.pk)
        self.gps.refresh_from_db()
        self.v1.refresh_from_db()
        self.assertEqual(self.gps.veiculo_id, self.v1.pk)
        self.assertEqual(self.v1.traccar_device_id, 55)

    def test_desvincular_limpa_campo_legado(self):
        associar_dispositivo(self.gps.pk, self.v1.pk)
        associar_dispositivo(self.gps.pk, None)
        self.gps.refresh_from_db()
        self.v1.refresh_from_db()
        self.assertIsNone(self.gps.veiculo_id)
        self.assertIsNone(self.v1.traccar_device_id)

    def test_proibe_troca_direta_entre_veiculos(self):
        associar_dispositivo(self.gps.pk, self.v1.pk)
        with self.assertRaises(ConflitoAssociacaoGPS):
            associar_dispositivo(self.gps.pk, self.v2.pk)
        self.gps.refresh_from_db()
        self.assertEqual(self.gps.veiculo_id, self.v1.pk)

    def test_nao_associa_gps_inativo(self):
        self.gps.ativo = False
        self.gps.save(update_fields=['ativo'])
        with self.assertRaises(ConflitoAssociacaoGPS):
            associar_dispositivo(self.gps.pk, self.v1.pk)

    def test_proibe_outro_gps_no_mesmo_veiculo(self):
        associar_dispositivo(self.gps.pk, self.v1.pk)
        outro = DispositivoGPS.objects.create(nome='GPS 2', traccar_id=56)
        with self.assertRaises(ConflitoAssociacaoGPS):
            associar_dispositivo(outro.pk, self.v1.pk)
        outro.refresh_from_db()
        self.assertIsNone(outro.veiculo_id)

    def test_proibe_sobrescrever_vinculo_legado_desconhecido(self):
        self.v1.traccar_device_id = 999
        self.v1.save(update_fields=['traccar_device_id'])
        with self.assertRaises(ConflitoAssociacaoGPS):
            associar_dispositivo(self.gps.pk, self.v1.pk)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.traccar_device_id, 999)

    def test_cadastro_veiculo_nao_expoe_identificador_legado(self):
        self.assertNotIn('traccar_device_id', VeiculoForm().fields)


class PermissoesEViewsTestes(UtilitariosGPS, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('gestor', password='senha-ficticia')
        self.client.force_login(self.user)
        self.gps = DispositivoGPS.objects.create(nome='GPS', traccar_id=77, unique_id='GPS77')
        self.v1 = self.veiculo('ABC1D23')

    def conceder(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='rastreamento', codename__in=codenames,
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)

    def test_usuario_sem_permissao_nao_acessa_tela_nem_importa_ou_associa(self):
        self.assertEqual(self.client.get(reverse('gps_dispositivos')).status_code, 403)
        self.assertEqual(self.client.post(reverse('gps_importar')).status_code, 403)
        self.assertEqual(self.client.post(reverse('gps_associar', args=[self.gps.pk]), {
            'veiculo': str(self.v1.pk),
        }).status_code, 403)

    def test_usuario_anonimo_e_redirecionado(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('gps_dispositivos')).status_code, 302)

    def test_leitura_nao_autoriza_importacao(self):
        self.conceder('view_dispositivogps')
        self.assertEqual(self.client.get(reverse('gps_dispositivos')).status_code, 200)
        self.assertEqual(self.client.post(reverse('gps_importar')).status_code, 403)

    @patch('rastreamento.views.sincronizar_dispositivos')
    def test_importacao_somente_post_e_com_permissao(self, sincronizar):
        self.conceder('view_dispositivogps', 'add_dispositivogps')
        self.assertEqual(self.client.get(reverse('gps_importar')).status_code, 405)
        sincronizar.assert_not_called()
        sincronizar.return_value = {'criados': 1, 'atualizados': 0}
        self.assertEqual(self.client.post(reverse('gps_importar')).status_code, 302)
        sincronizar.assert_called_once()

    def test_vincular_pelo_formulario(self):
        self.conceder('change_dispositivogps')
        resposta = self.client.post(reverse('gps_associar', args=[self.gps.pk]), {
            'veiculo': str(self.v1.pk),
        })
        self.assertEqual(resposta.status_code, 302)
        self.gps.refresh_from_db()
        self.v1.refresh_from_db()
        self.assertEqual(self.gps.veiculo_id, self.v1.pk)
        self.assertEqual(self.v1.traccar_device_id, self.gps.traccar_id)

    def test_csrf_obrigatorio_na_importacao(self):
        self.conceder('add_dispositivogps')
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        self.assertEqual(cliente.post(reverse('gps_importar')).status_code, 403)
