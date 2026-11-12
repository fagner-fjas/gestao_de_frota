"""Cenários críticos do módulo recorrente, com banco de testes Django."""
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from frota.models import Motorista, Passageiro, ProgramacaoRecorrente, Rota, Veiculo, Viagem
from frota.services.recorrencias import gerar_viagens


class RecorrenciaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user('gestor', password='senha-teste', is_staff=True)
        cls.comum = get_user_model().objects.create_user('comum', password='senha-teste')
        cls.rota = Rota.objects.create(nome='Escola manhã', origem='A', destino='Escola',
                                       distancia_km=10, duracao_minutos=45)
        cls.veiculo = Veiculo.objects.create(
            placa='ABC1234', marca='M', modelo='Van', ano=2020,
            tipo=Veiculo.Tipo.VAN, capacidade=3,
        )
        cls.veiculo2 = Veiculo.objects.create(
            placa='DEF5678', marca='M', modelo='Van', ano=2020,
            tipo=Veiculo.Tipo.VAN, capacidade=5,
        )
        cls.motorista = Motorista.objects.create(
            nome='José', cpf='12345678901', data_nascimento=date(1990, 1, 1),
            cnh_numero='11111111111', cnh_categoria='D',
            cnh_validade=timezone.localdate() + timedelta(days=730), telefone='123',
        )
        cls.motorista2 = Motorista.objects.create(
            nome='Carlos', cpf='12345678902', data_nascimento=date(1990, 1, 1),
            cnh_numero='22222222222', cnh_categoria='D',
            cnh_validade=timezone.localdate() + timedelta(days=730), telefone='123',
        )
        cls.passageiro = Passageiro.objects.create(nome='Estudante', documento='100', telefone='123')
        cls.passageiro2 = Passageiro.objects.create(nome='Estudante 2', documento='101', telefone='123')
        hoje = timezone.localdate()
        cls.segunda = hoje + timedelta(days=(7 - hoje.weekday()) % 7 + 7)

    def setUp(self):
        self.programacao = ProgramacaoRecorrente.objects.create(
            nome='Escola — 06h30', rota=self.rota, motorista_padrao=self.motorista,
            veiculo_padrao=self.veiculo, dias_semana='0,1,2,3,4',
            hora_partida='06:30', data_inicio=self.segunda,
            data_fim=self.segunda + timedelta(days=14),
        )
        self.programacao.passageiros.add(self.passageiro, self.passageiro2)
        self.client.force_login(self.staff)

    def test_gera_apenas_dias_uteis_e_clona_vinculos(self):
        fim = self.segunda + timedelta(days=6)
        resultado = gerar_viagens(self.programacao.pk, self.segunda, fim)
        self.assertEqual(resultado.criadas, 5)
        self.assertEqual(resultado.existentes, 0)
        self.assertEqual(Viagem.objects.count(), 5)
        self.assertTrue(all(v.programacao_recorrente_id == self.programacao.pk for v in Viagem.objects.all()))
        self.assertEqual(Viagem.objects.first().passageiros.count(), 2)

    def test_idempotencia_e_preservacao_de_alteracoes(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        viagem.motorista = self.motorista2
        viagem.save(update_fields=['motorista'])
        resultado = gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem.refresh_from_db()
        self.assertEqual((resultado.criadas, resultado.existentes), (0, 1))
        self.assertEqual(viagem.motorista_id, self.motorista2.pk)

    def test_cancelada_nao_e_recriada(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        viagem.status = Viagem.Status.CANCELADA
        viagem.save(update_fields=['status'])
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        self.assertEqual(Viagem.objects.count(), 1)
        self.assertEqual(Viagem.objects.get().status, Viagem.Status.CANCELADA)

    def test_conflito_com_viagem_manual_impede_geracao(self):
        partida = timezone.make_aware(datetime.combine(self.segunda, datetime.strptime('06:30', '%H:%M').time()))
        Viagem.objects.create(data_hora_partida=partida, rota=self.rota,
                              veiculo=self.veiculo, motorista=self.motorista)
        r = gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        self.assertEqual(r.criadas, 0)
        self.assertEqual(len(r.recusadas), 1)

    def test_limites_do_periodo(self):
        with self.assertRaises(ValidationError):
            gerar_viagens(self.programacao.pk, self.segunda, self.segunda + timedelta(days=31))
        with self.assertRaises(ValidationError):
            gerar_viagens(self.programacao.pk, self.segunda + timedelta(days=2), self.segunda)
        with self.assertRaises(ValidationError):
            gerar_viagens(self.programacao.pk, timezone.localdate() - timedelta(days=1), self.segunda)

    def test_nenhum_veiculo_com_capacidade_insuficiente(self):
        self.veiculo.capacidade = 1
        self.veiculo.save(update_fields=['capacidade'])
        with self.assertRaises(ValidationError):
            gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        self.assertFalse(Viagem.objects.exists())

    def test_formulario_programacao_rejeita_semana_sem_dias(self):
        dados = {
            'nome': 'Exemplo', 'rota': self.rota.pk,
            'motorista_padrao': self.motorista.pk, 'veiculo_padrao': self.veiculo.pk,
            'hora_partida': '06:30', 'data_inicio': self.segunda.isoformat(),
            'data_fim': (self.segunda + timedelta(days=5)).isoformat(),
            'passageiros': [self.passageiro.pk], 'ativa': 'on',
        }
        resposta = self.client.post(reverse('programacao_nova'), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('dias_semana', resposta.context['form'].errors)

    def test_permissao_nega_geracao_para_usuario_comum(self):
        self.client.force_login(self.comum)
        resposta = self.client.post(reverse('programacao_gerar', args=[self.programacao.pk]), {
            'inicio': self.segunda.isoformat(), 'fim': self.segunda.isoformat(),
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Viagem.objects.exists())

    def test_formulario_geracao_e_api_repetida(self):
        url = reverse('programacao_gerar', args=[self.programacao.pk])
        dados = {'inicio': self.segunda.isoformat(), 'fim': self.segunda.isoformat()}
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(Viagem.objects.count(), 1)

    def test_confirmacao_e_inicio_exigem_etapas(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        self.client.post(reverse('viagem_status', args=[viagem.pk, 'iniciar']))
        viagem.refresh_from_db()
        self.assertEqual(viagem.status, Viagem.Status.AGENDADA)
        url = reverse('viagem_confirmar_recorrente', args=[viagem.pk])
        resposta = self.client.post(url, {
            'motorista': self.motorista2.pk, 'veiculo': self.veiculo2.pk,
            'passageiros_embarcados': 2,
        })
        self.assertEqual(resposta.status_code, 302)
        viagem.refresh_from_db()
        self.assertEqual(viagem.motorista_id, self.motorista2.pk)
        self.assertEqual(viagem.veiculo_id, self.veiculo2.pk)
        self.assertEqual(viagem.passageiros_embarcados, 2)
        self.assertEqual(viagem.confirmado_por_id, self.staff.pk)
        self.assertIsNotNone(viagem.confirmado_em)
        self.client.post(reverse('viagem_status', args=[viagem.pk, 'iniciar']))
        viagem.refresh_from_db()
        self.assertEqual(viagem.status, Viagem.Status.EM_ANDAMENTO)

    def test_usuario_comum_nao_pode_mudar_status_recorrente(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        self.client.force_login(self.comum)
        self.assertEqual(self.client.post(
            reverse('viagem_status', args=[viagem.pk, 'cancelar'])
        ).status_code, 403)
        self.assertEqual(self.client.get(
            reverse('viagem_editar', args=[viagem.pk])
        ).status_code, 403)
        viagem.refresh_from_db()
        self.assertEqual(viagem.status, Viagem.Status.AGENDADA)

    def test_capacidade_real_e_protecao_da_exclusao(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        url = reverse('viagem_confirmar_recorrente', args=[viagem.pk])
        resposta = self.client.post(url, {
            'motorista': self.motorista.pk, 'veiculo': self.veiculo.pk,
            'passageiros_embarcados': 7,
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'capacidade')
        self.client.post(reverse('viagem_excluir', args=[viagem.pk]))
        self.assertTrue(Viagem.objects.filter(pk=viagem.pk).exists())

    def test_nao_pode_mover_recorrente_de_dia(self):
        gerar_viagens(self.programacao.pk, self.segunda, self.segunda)
        viagem = Viagem.objects.get()
        novo_dia = self.segunda + timedelta(days=1)
        self.client.post(reverse('viagem_editar', args=[viagem.pk]), {
            'data_hora_partida': f'{novo_dia.isoformat()}T06:30',
            'rota': self.rota.pk, 'veiculo': self.veiculo.pk,
            'motorista': self.motorista.pk, 'passageiros': [self.passageiro.pk],
        })
        viagem.refresh_from_db()
        self.assertEqual(viagem.data_programada, self.segunda)
        self.assertEqual(timezone.localtime(viagem.data_hora_partida).date(), self.segunda)

    def test_comando_idempotente(self):
        call_command('gerar_recorrencias', dias=31)
        quantidade = Viagem.objects.count()
        call_command('gerar_recorrencias', dias=31)
        self.assertEqual(Viagem.objects.count(), quantidade)
