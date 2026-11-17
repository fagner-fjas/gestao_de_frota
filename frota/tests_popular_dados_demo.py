"""Testes de regressão do comando de criação de dados fictícios."""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from frota.models import Motorista, Passageiro, ProgramacaoRecorrente, Rota, Veiculo, Viagem


class PopularDadosDemoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        hoje = timezone.localdate()
        cls.inicio = hoje + timedelta(days=(7 - hoje.weekday()) % 7 or 7)

    def executar(self, **opcoes):
        destino = StringIO()
        argumentos = dict(inicio=self.inicio.isoformat(), dias=7, stdout=destino)
        argumentos.update(opcoes)
        call_command('popular_dados_demo', **argumentos)
        return destino.getvalue()

    def test_popula_viagens_recorrentes_e_avulsas(self):
        saida = self.executar()
        self.assertIn('Dados DEMO:', saida)
        self.assertEqual(Rota.objects.filter(nome__startswith='DEMO |').count(), 4)
        self.assertEqual(Veiculo.objects.filter(placa__startswith='DEM').count(), 4)
        self.assertEqual(Motorista.objects.filter(nome__startswith='Motorista DEMO').count(), 4)
        self.assertEqual(Passageiro.objects.filter(documento__startswith='DEMO-ALUNO').count(), 16)
        self.assertEqual(ProgramacaoRecorrente.objects.count(), 4)
        self.assertEqual(Viagem.objects.filter(programacao_recorrente__isnull=False).count(), 20)
        self.assertEqual(Viagem.objects.filter(programacao_recorrente__isnull=True).count(), 2)
        for programacao in ProgramacaoRecorrente.objects.all():
            self.assertEqual(programacao.passageiros.count(), 8)
        self.assertEqual(Viagem.objects.count(), 22)

    def test_reexecucao_nao_duplica_nem_sobrescreve(self):
        self.executar()
        veiculo = Veiculo.objects.get(placa='DEM1A01')
        veiculo.marca = 'Marca alterada pelo usuário'
        veiculo.save(update_fields=['marca'])
        self.executar()
        self.assertEqual(Viagem.objects.count(), 22)
        self.assertEqual(ProgramacaoRecorrente.objects.count(), 4)
        veiculo.refresh_from_db()
        self.assertEqual(veiculo.marca, 'Marca alterada pelo usuário')

    def test_sem_gerar_mantem_programacoes_e_dados_avulsos(self):
        self.executar(sem_gerar=True)
        self.assertEqual(ProgramacaoRecorrente.objects.count(), 4)
        self.assertEqual(Viagem.objects.filter(programacao_recorrente__isnull=False).count(), 0)
        self.assertEqual(Viagem.objects.filter(programacao_recorrente__isnull=True).count(), 2)

    def test_dias_invalidos_falham_sem_criar_dados(self):
        with self.assertRaises(CommandError):
            self.executar(dias=0)
        self.assertFalse(Rota.objects.exists())
