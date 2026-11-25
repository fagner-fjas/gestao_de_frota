from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ProgramacaoRecorrenteForm, ViagemForm
from .models import Motorista, Passageiro, ProgramacaoRecorrente, Rota, Veiculo, Viagem


class SeletorPassageirosTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username='gestor_seletor', password='senha-teste', is_staff=True
        )
        cls.rota = Rota.objects.create(
            nome='Rota seletor', origem='Centro', destino='Escola',
            distancia_km=12, duracao_minutos=35,
        )
        cls.veiculo = Veiculo.objects.create(
            placa='QWE1A23', marca='Mercedes', modelo='Van', ano=2020,
            tipo=Veiculo.Tipo.VAN, capacidade=10,
        )
        cls.motorista = Motorista.objects.create(
            nome='Motorista de teste', cpf='12345678901',
            data_nascimento=date(1990, 1, 1), cnh_numero='12345678901',
            cnh_categoria='D', cnh_validade=date.today() + timedelta(days=700),
            telefone='11999999999',
        )
        cls.ativo = Passageiro.objects.create(
            nome='Ana Teste', documento='123.456.789-00', telefone='111', ativo=True
        )
        cls.inativo = Passageiro.objects.create(
            nome='Bruno Teste', documento='987.654.321-00', telefone='222', ativo=False
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_formulario_viagem_nova_utiliza_modal(self):
        resposta = self.client.get(reverse('viagem_nova'))
        self.assertContains(resposta, 'data-passenger-picker')
        self.assertContains(resposta, 'Selecionar passageiros')
        self.assertContains(resposta, 'Adicionar passageiros')
        self.assertContains(resposta, 'seletor_passageiros.js')

    def test_formulario_recorrente_utiliza_mesmo_modal(self):
        resposta = self.client.get(reverse('programacao_nova'))
        self.assertContains(resposta, 'data-passenger-picker')
        self.assertContains(resposta, 'data-ps-apply')
        self.assertContains(resposta, 'seletor_passageiros.css')

    def test_documento_e_situacao_disponiveis_na_interface(self):
        html = str(ViagemForm()['passageiros'])
        self.assertIn('data-documento="123.456.789-00"', html)
        self.assertIn('data-ativo="true"', html)
        self.assertNotIn('987.654.321-00', html)

    def test_edicao_mantem_passageiro_inativado_ja_vinculado(self):
        partida = timezone.now() + timedelta(days=3)
        viagem = Viagem.objects.create(
            data_hora_partida=partida, rota=self.rota,
            motorista=self.motorista, veiculo=self.veiculo,
        )
        viagem.passageiros.add(self.inativo)
        html = str(ViagemForm(instance=viagem)['passageiros'])
        self.assertIn('987.654.321-00', html)
        self.assertIn('data-ativo="false"', html)
        self.assertIn('checked', html)

    def test_recorrencia_preserva_inativo_e_identifica_vinculo(self):
        hoje = timezone.localdate() + timedelta(days=1)
        programacao = ProgramacaoRecorrente.objects.create(
            nome='Programação demonstrativa', rota=self.rota,
            motorista_padrao=self.motorista, veiculo_padrao=self.veiculo,
            dias_semana='0,1,2,3,4', hora_partida='06:30',
            data_inicio=hoje,
        )
        programacao.passageiros.add(self.inativo)
        html = str(ProgramacaoRecorrenteForm(instance=programacao)['passageiros'])
        self.assertIn('987.654.321-00', html)
        self.assertIn('data-vinculado="true"', html)
        self.assertIn('checked', html)
