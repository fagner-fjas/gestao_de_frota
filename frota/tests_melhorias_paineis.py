"""Regressão dos filtros e da fila operacional (UX-02, UX-03, UX-09)."""
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Motorista, ProgramacaoRecorrente, Rota, Veiculo, Viagem


class PainelOperacionalUXTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='gestor_ux', password='senha-teste-ux', is_staff=True
        )
        self.client.force_login(self.user)
        self.rota = Rota.objects.create(
            nome='Rota Centro', origem='Centro', destino='Escola',
            distancia_km=4, duracao_minutos=30
        )
        self.rota2 = Rota.objects.create(
            nome='Rota Norte', origem='Norte', destino='Escola',
            distancia_km=5, duracao_minutos=30
        )
        self.veiculo = Veiculo.objects.create(
            placa='ABC1234', marca='M', modelo='Van', ano=2020,
            tipo='VAN', capacidade=20
        )
        self.motorista = Motorista.objects.create(
            nome='Motorista Demo', cpf='111.111.111-11',
            data_nascimento=date(1990, 1, 1), cnh_numero='12345678901',
            cnh_categoria='D', cnh_validade=date.today() + timedelta(days=365),
            telefone='111'
        )
        self.hoje = timezone.localdate()
        self.programacao = ProgramacaoRecorrente.objects.create(
            nome='Centro Ida', rota=self.rota, motorista_padrao=self.motorista,
            veiculo_padrao=self.veiculo, dias_semana='0,1,2,3,4',
            hora_partida=time(6, 30), data_inicio=self.hoje - timedelta(days=7)
        )

    def criar_viagem(self, rota=None, dias=0, recorrente=True, confirmado=False):
        data = self.hoje + timedelta(days=dias)
        hora = timezone.make_aware(datetime.combine(data, time(6, 30)))
        return Viagem.objects.create(
            rota=rota or self.rota, veiculo=self.veiculo, motorista=self.motorista,
            data_hora_partida=hora,
            programacao_recorrente=self.programacao if recorrente else None,
            data_programada=data if recorrente else None,
            confirmado_em=timezone.now() if confirmado else None,
        )

    def test_filtro_viagem_por_data_rota_e_pendencia(self):
        esperada = self.criar_viagem()
        self.criar_viagem(rota=self.rota2, recorrente=False)
        self.criar_viagem(dias=1, recorrente=False)
        url = reverse('viagem_lista')
        resposta = self.client.get(url, {
            'data': self.hoje.isoformat(), 'rota': self.rota.pk, 'pendente': '1'
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([v.pk for v in resposta.context['object_list']], [esperada.pk])
        self.assertContains(resposta, 'Pendentes de confirmação')

    def test_dashboard_tem_fila_do_dia(self):
        self.criar_viagem()
        self.criar_viagem(dias=1)
        resposta = self.client.get(reverse('plataforma'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.context['viagens_hoje']), 1)
        self.assertContains(resposta, 'Aguardando confirmação')
        self.assertContains(resposta, 'Confirmar')

    def test_recorrencia_exibe_proximos_dias_e_vinculos(self):
        resposta = self.client.get(reverse('programacao_lista'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Centro Ida')
        self.assertContains(resposta, 'Seg, Ter, Qua, Qui, Sex')
        self.assertContains(resposta, 'Próxima operação')

    def test_filtro_recorrencias_por_rota_e_estado(self):
        ProgramacaoRecorrente.objects.create(
            nome='Outra programação', rota=self.rota2,
            motorista_padrao=self.motorista, veiculo_padrao=self.veiculo,
            dias_semana='0,1,2,3,4', hora_partida=time(7),
            data_inicio=self.hoje, ativa=False
        )
        resposta = self.client.get(reverse('programacao_lista'),
                                   {'rota': self.rota.pk, 'ativa': '1'})
        self.assertEqual(len(resposta.context['object_list']), 1)
        self.assertContains(resposta, 'Centro Ida')
        self.assertNotContains(resposta, 'Outra programação')
