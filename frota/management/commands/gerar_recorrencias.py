"""Geração diária opcional. Ex.: python manage.py gerar_recorrencias --dias 7."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from frota.models import ProgramacaoRecorrente
from frota.services.recorrencias import gerar_viagens


class Command(BaseCommand):
    help = 'Gera viagens futuras das programações ativas; idempotente (máximo de 31 dias).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=7, help='Quantidade de dias, de 1 a 31.')

    def handle(self, *args, **options):
        dias = options['dias']
        if not 1 <= dias <= 31:
            raise CommandError('--dias deve ser um número entre 1 e 31.')
        hoje = timezone.localdate()
        ultimo = hoje + timedelta(days=dias - 1)
        total_criadas = total_existentes = total_recusadas = 0
        for programacao in ProgramacaoRecorrente.objects.filter(ativa=True):
            inicio = max(hoje, programacao.data_inicio)
            fim = min(ultimo, programacao.data_fim) if programacao.data_fim else ultimo
            if inicio > fim:
                continue
            try:
                r = gerar_viagens(programacao.pk, inicio, fim)
            except ValidationError as erro:
                self.stderr.write(f'{programacao.pk} - {programacao.nome}: {"; ".join(erro.messages)}')
                continue
            total_criadas += r.criadas
            total_existentes += r.existentes
            total_recusadas += len(r.recusadas)
            for erro in r.recusadas:
                self.stderr.write(f'{programacao.nome}: {erro}')
        self.stdout.write(self.style.SUCCESS(
            f'Criadas={total_criadas}; existentes={total_existentes}; recusadas={total_recusadas}'
        ))
