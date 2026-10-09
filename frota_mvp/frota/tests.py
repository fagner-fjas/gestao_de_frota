from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Motorista, Passageiro, Rota, Veiculo, Viagem


class BaseTeste(TestCase):
    def setUp(self):
        User.objects.create_user('teste', password='senha12345')
        self.client.login(username='teste', password='senha12345')


class RotaCrudTest(BaseTeste):
    def test_crud_completo(self):
        dados = {'nome': 'R1', 'origem': 'Sumé', 'destino': 'Patos',
                 'distancia_km': '130.5', 'duracao_minutos': 120, 'ativa': 'on'}
        self.assertRedirects(self.client.post(reverse('rota_nova'), dados), reverse('rota_lista'))
        rota = Rota.objects.get()
        self.assertContains(self.client.get(reverse('rota_lista')), 'Sumé')
        self.assertContains(self.client.get(reverse('rota_lista') + '?q=patos'), 'R1')
        self.assertNotContains(self.client.get(reverse('rota_lista') + '?q=xyz'), 'R1</td>')
        self.assertContains(self.client.get(reverse('rota_detalhe', args=[rota.pk])), 'Patos')
        dados['destino'] = 'Campina Grande'
        self.client.post(reverse('rota_editar', args=[rota.pk]), dados)
        rota.refresh_from_db()
        self.assertEqual(rota.destino, 'Campina Grande')
        self.client.post(reverse('rota_excluir', args=[rota.pk]))
        self.assertEqual(Rota.objects.count(), 0)

    def test_validacoes(self):
        Rota.objects.create(nome='R1', origem='A', destino='B', distancia_km=10, duracao_minutos=30)
        r = self.client.post(reverse('rota_nova'), {
            'nome': 'R1', 'origem': 'A', 'destino': 'B', 'distancia_km': '-5', 'duracao_minutos': 30})
        self.assertEqual(Rota.objects.count(), 1)
        self.assertContains(r, 'errorlist')

    def test_paginacao(self):
        for i in range(25):
            Rota.objects.create(nome=f'R{i:02d}', origem='A', destino='B',
                                distancia_km=10, duracao_minutos=30)
        r = self.client.get(reverse('rota_lista'))
        self.assertEqual(len(r.context['linhas']), 20)
        r = self.client.get(reverse('rota_lista') + '?page=2')
        self.assertEqual(len(r.context['linhas']), 5)


class MotoristaCrudTest(BaseTeste):
    def dados(self, **extra):
        base = {'nome': 'João', 'cpf': '12345678901', 'data_nascimento': '1990-05-10',
                'cnh_numero': '12345678901', 'cnh_categoria': 'D',
                'cnh_validade': (date.today() + timedelta(days=400)).isoformat(),
                'telefone': '8399999999', 'ativo': 'on'}
        base.update(extra)
        return base

    def test_crud_completo(self):
        self.client.post(reverse('motorista_nova'), self.dados())
        m = Motorista.objects.get()
        self.assertEqual(m.cpf, '123.456.789-01')
        self.assertContains(self.client.get(reverse('motorista_lista') + '?q=123.456'), 'João')
        self.client.post(reverse('motorista_editar', args=[m.pk]), self.dados(nome='João Silva'))
        m.refresh_from_db()
        self.assertEqual(m.nome, 'João Silva')
        self.client.post(reverse('motorista_excluir', args=[m.pk]))
        self.assertEqual(Motorista.objects.count(), 0)

    def test_validacoes(self):
        vencida = (date.today() - timedelta(days=1)).isoformat()
        self.assertContains(self.client.post(reverse('motorista_nova'), self.dados(cnh_validade=vencida)), 'CNH vencida')
        self.assertContains(self.client.post(reverse('motorista_nova'), self.dados(cpf='123')), '11 dígitos')
        self.assertContains(self.client.post(
            reverse('motorista_nova'), self.dados(data_nascimento=date.today().isoformat())), 'maior de 18')
        self.assertEqual(Motorista.objects.count(), 0)


class VeiculoCrudTest(BaseTeste):
    def dados(self, **extra):
        base = {'placa': 'abc-1d23', 'marca': 'Mercedes', 'modelo': 'Sprinter', 'ano': 2020,
                'tipo': 'VAN', 'capacidade': 15, 'quilometragem': 1000, 'situacao': 'DISPONIVEL'}
        base.update(extra)
        return base

    def test_crud_completo(self):
        self.client.post(reverse('veiculo_nova'), self.dados())
        v = Veiculo.objects.get()
        self.assertEqual(v.placa, 'ABC1D23')
        self.assertContains(self.client.get(reverse('veiculo_lista') + '?q=sprint'), 'ABC1D23')
        self.client.post(reverse('veiculo_editar', args=[v.pk]), self.dados(capacidade=20))
        v.refresh_from_db()
        self.assertEqual(v.capacidade, 20)
        self.client.post(reverse('veiculo_excluir', args=[v.pk]))
        self.assertEqual(Veiculo.objects.count(), 0)

    def test_placa_invalida(self):
        self.assertContains(self.client.post(reverse('veiculo_nova'), self.dados(placa='12')), 'Placa inválida')


class PassageiroCrudTest(BaseTeste):
    def test_crud_completo(self):
        dados = {'nome': 'Maria', 'documento': '111', 'telefone': '8388888888', 'ativo': 'on'}
        self.client.post(reverse('passageiro_nova'), dados)
        p = Passageiro.objects.get()
        self.assertContains(self.client.get(reverse('passageiro_lista') + '?q=mar'), 'Maria')
        dados['nome'] = 'Maria Souza'
        self.client.post(reverse('passageiro_editar', args=[p.pk]), dados)
        p.refresh_from_db()
        self.assertEqual(p.nome, 'Maria Souza')
        self.client.post(reverse('passageiro_excluir', args=[p.pk]))
        self.assertEqual(Passageiro.objects.count(), 0)


class ViagemTest(BaseTeste):
    def setUp(self):
        super().setUp()
        self.rota = Rota.objects.create(nome='R1', origem='A', destino='B',
                                        distancia_km=100, duracao_minutos=120)
        self.veiculo = Veiculo.objects.create(placa='ABC1234', marca='M', modelo='Van', ano=2020,
                                              tipo='VAN', capacidade=2)
        self.veiculo2 = Veiculo.objects.create(placa='DEF5678', marca='M', modelo='Van', ano=2020,
                                               tipo='VAN', capacidade=5)
        validade = date.today() + timedelta(days=365)
        self.mot = Motorista.objects.create(nome='João', cpf='111.111.111-11', data_nascimento='1990-01-01',
                                            cnh_numero='11111111111', cnh_categoria='D',
                                            cnh_validade=validade, telefone='1')
        self.mot2 = Motorista.objects.create(nome='Pedro', cpf='222.222.222-22', data_nascimento='1990-01-01',
                                             cnh_numero='22222222222', cnh_categoria='D',
                                             cnh_validade=validade, telefone='1')
        self.ps = [Passageiro.objects.create(nome=f'P{i}', documento=str(i), telefone='1') for i in range(3)]
        self.partida = (timezone.localtime() + timedelta(days=2)).replace(second=0, microsecond=0)

    def dados(self, **extra):
        base = {'data_hora_partida': self.partida.strftime('%Y-%m-%dT%H:%M'),
                'rota': self.rota.pk, 'veiculo': self.veiculo.pk, 'motorista': self.mot.pk,
                'passageiros': [self.ps[0].pk]}
        base.update(extra)
        return base

    def test_crud_completo(self):
        self.assertRedirects(self.client.post(reverse('viagem_nova'), self.dados()), reverse('viagem_lista'))
        v = Viagem.objects.get()
        self.assertEqual(v.status, 'AGENDADA')
        self.assertContains(self.client.get(reverse('viagem_lista') + '?q=ABC1234'), 'R1')
        self.assertContains(self.client.get(reverse('viagem_lista') + '?status=AGENDADA'), 'R1')
        self.assertNotContains(self.client.get(reverse('viagem_lista') + '?status=CONCLUIDA'), 'ABC1234')
        self.assertContains(self.client.get(reverse('viagem_detalhe', args=[v.pk])), 'P0')
        self.client.post(reverse('viagem_editar', args=[v.pk]),
                         self.dados(passageiros=[self.ps[0].pk, self.ps[1].pk]))
        self.assertEqual(v.passageiros.count(), 2)
        self.client.post(reverse('viagem_excluir', args=[v.pk]))
        self.assertEqual(Viagem.objects.count(), 0)

    def test_data_no_passado(self):
        passado = (timezone.localtime() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.assertContains(self.client.post(reverse('viagem_nova'), self.dados(data_hora_partida=passado)), 'passado')

    def test_capacidade(self):
        r = self.client.post(reverse('viagem_nova'), self.dados(passageiros=[p.pk for p in self.ps]))
        self.assertContains(r, 'comporta 2')
        self.assertEqual(Viagem.objects.count(), 0)

    def test_conflito_agenda(self):
        self.client.post(reverse('viagem_nova'), self.dados())
        outra = (self.partida + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        r = self.client.post(reverse('viagem_nova'), self.dados(data_hora_partida=outra))
        self.assertContains(r, 'Veículo já alocado')
        self.assertContains(r, 'Motorista já alocado')
        self.assertEqual(Viagem.objects.count(), 1)
        self.client.post(reverse('viagem_nova'), self.dados(
            veiculo=self.veiculo2.pk, motorista=self.mot2.pk, passageiros=[self.ps[1].pk]))
        self.assertEqual(Viagem.objects.count(), 2)
        depois = (self.partida + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('viagem_nova'), self.dados(
            data_hora_partida=depois, motorista=self.mot2.pk, passageiros=[self.ps[2].pk]))
        self.assertEqual(Viagem.objects.count(), 3)

    def test_cnh_vencida_na_data_da_viagem(self):
        self.mot.cnh_validade = date.today() + timedelta(days=1)
        self.mot.save()
        self.assertContains(self.client.post(reverse('viagem_nova'), self.dados()), 'vencida na data da viagem')

    def test_fluxo_de_status_e_situacao_do_veiculo(self):
        self.client.post(reverse('viagem_nova'), self.dados())
        v = Viagem.objects.get()
        self.client.post(reverse('viagem_status', args=[v.pk, 'iniciar']))
        v.refresh_from_db()
        self.veiculo.refresh_from_db()
        self.assertEqual((v.status, self.veiculo.situacao), ('EM_ANDAMENTO', 'EM_VIAGEM'))
        r = self.client.get(reverse('viagem_editar', args=[v.pk]))
        self.assertRedirects(r, reverse('viagem_detalhe', args=[v.pk]))
        self.client.post(reverse('viagem_status', args=[v.pk, 'concluir']))
        v.refresh_from_db()
        self.veiculo.refresh_from_db()
        self.assertEqual((v.status, self.veiculo.situacao), ('CONCLUIDA', 'DISPONIVEL'))

    def test_exclusao_protegida_por_viagem(self):
        self.client.post(reverse('viagem_nova'), self.dados())
        for nome, obj in [('rota_excluir', self.rota), ('veiculo_excluir', self.veiculo),
                          ('motorista_excluir', self.mot)]:
            r = self.client.post(reverse(nome, args=[obj.pk]), follow=True)
            self.assertContains(r, 'existem viagens vinculadas')
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
