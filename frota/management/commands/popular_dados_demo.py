"""Popula o banco de desenvolvimento com dados fictícios identificados como DEMO.

Exemplo:
    python manage.py popular_dados_demo --dias 14

Este comando não apaga dados, não modifica registros existentes e não gera
credenciais, usuários ou dispositivos Traccar.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from frota.models import Motorista, Passageiro, ProgramacaoRecorrente, Rota, Veiculo, Viagem
from frota.services.agenda import conflitos_de_agenda
from frota.services.recorrencias import gerar_viagens


# Nomes e identificadores explicitamente fictícios. Não correspondem a
# estudantes, condutores ou veículos reais.
ROTAS = (
    ('DEMO | Centro - Escola (ida)', 'Bairro Centro (fictício)', 'Escola DEMO', '4.5', 25),
    ('DEMO | Escola - Centro (volta)', 'Escola DEMO', 'Bairro Centro (fictício)', '4.5', 25),
    ('DEMO | Bairro Norte - Escola (ida)', 'Bairro Norte (fictício)', 'Escola DEMO', '6.8', 35),
    ('DEMO | Escola - Bairro Norte (volta)', 'Escola DEMO', 'Bairro Norte (fictício)', '6.8', 35),
)

VEICULOS = (
    ('DEM1A01', 'Mercedes-Benz', 'Sprinter DEMO', Veiculo.Tipo.VAN, 18),
    ('DEM1A02', 'Fiat', 'Ducato DEMO', Veiculo.Tipo.VAN, 18),
    ('DEM1A03', 'Volare', 'Micro-ônibus DEMO', Veiculo.Tipo.MICROONIBUS, 25),
    ('DEM1A04', 'Volkswagen', 'Micro-ônibus DEMO', Veiculo.Tipo.MICROONIBUS, 25),
)

PROGRAMACOES = (
    # Nome, índice da rota, índice do motorista, índice do veículo,
    # conjunto de passageiros e horário de partida.
    ('DEMO | Centro - ida 06h30', 0, 0, 0, 0, time(6, 30)),
    ('DEMO | Centro - volta 12h15', 1, 1, 1, 0, time(12, 15)),
    ('DEMO | Bairro Norte - ida 06h45', 2, 2, 2, 1, time(6, 45)),
    ('DEMO | Bairro Norte - volta 12h30', 3, 3, 3, 1, time(12, 30)),
)


class Command(BaseCommand):
    help = (
        'Cria dados fictícios DEMO (rotas, veículos, motoristas, passageiros, '
        'programações e viagens) sem apagar registros existentes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias', type=int, default=14,
            help='Quantidade de dias do período de demonstração (1 a 31, padrão: 14).',
        )
        parser.add_argument(
            '--inicio', type=str,
            help='Data inicial ISO 8601 (AAAA-MM-DD); padrão: próxima segunda-feira.',
        )
        parser.add_argument(
            '--sem-gerar', action='store_true',
            help='Cria programações e viagens manuais, mas não gera ocorrências recorrentes.',
        )

    def handle(self, *args, **options):
        dias = options['dias']
        if not 1 <= dias <= 31:
            raise CommandError('--dias deve estar entre 1 e 31.')

        hoje = timezone.localdate()
        if options['inicio']:
            try:
                inicio = date.fromisoformat(options['inicio'])
            except ValueError as exc:
                raise CommandError('--inicio deve estar no formato AAAA-MM-DD.') from exc
        else:
            # Próxima segunda-feira, mesmo quando executado em uma segunda.
            inicio = hoje + timedelta(days=(7 - hoje.weekday()) % 7 or 7)
        if inicio < hoje:
            raise CommandError('--inicio não pode estar no passado.')
        fim = inicio + timedelta(days=dias - 1)

        contador = dict(rotas=0, veiculos=0, motoristas=0,
                        passageiros=0, programacoes=0, manuais=0)

        with transaction.atomic():
            rotas = self._rotas(contador)
            veiculos = self._veiculos(contador)
            motoristas = self._motoristas(contador, fim)
            passageiros = self._passageiros(contador)
            programacoes = self._programacoes(
                contador, inicio, fim, rotas, veiculos, motoristas, passageiros
            )

            resumo = dict(criadas=0, existentes=0, recusadas=0)
            if not options['sem_gerar']:
                for programacao in programacoes:
                    # Ao reexecutar, nunca alteramos as datas de uma programação
                    # existente; geramos somente a interseção da vigência.
                    comeco = max(inicio, programacao.data_inicio)
                    termino = min(fim, programacao.data_fim) if programacao.data_fim else fim
                    if comeco > termino:
                        self.stdout.write(
                            f'Programação {programacao.nome}: nenhuma data na vigência existente.'
                        )
                        continue
                    try:
                        resultado = gerar_viagens(programacao.pk, comeco, termino)
                    except ValidationError as exc:
                        self.stderr.write(
                            f'Programação {programacao.nome}: {"; ".join(exc.messages)}'
                        )
                        resumo['recusadas'] += 1
                        continue
                    resumo['criadas'] += resultado.criadas
                    resumo['existentes'] += resultado.existentes
                    resumo['recusadas'] += len(resultado.recusadas)
                    for motivo in resultado.recusadas[:3]:
                        self.stderr.write(f'{programacao.nome}: {motivo}')
                    if len(resultado.recusadas) > 3:
                        self.stderr.write(
                            f'{programacao.nome}: mais {len(resultado.recusadas) - 3} recusas.'
                        )

            # Viagens avulsas servem para demonstrar o CRUD existente; ficam
            # fora da programação, com horário sem sobreposição com as recorrências.
            manuais = ((0, 0, 0, (0, 1), time(15, 0)),
                       (2, 2, 2, (8, 9), time(16, 0)))
            for i_rota, i_motorista, i_veiculo, indices, hora in manuais:
                partida = timezone.make_aware(
                    datetime.combine(inicio, hora), timezone.get_current_timezone()
                )
                rota, motorista, veiculo = (
                    rotas[i_rota], motoristas[i_motorista], veiculos[i_veiculo]
                )
                pessoas = [passageiros[i] for i in indices]
                existente = Viagem.objects.filter(
                    programacao_recorrente__isnull=True,
                    data_hora_partida=partida, rota=rota,
                    motorista=motorista, veiculo=veiculo,
                ).first()
                if existente:
                    continue
                if conflitos_de_agenda(partida, rota, veiculo, motorista, pessoas):
                    self.stderr.write(
                        f'Viagem manual DEMO das {hora:%H:%M}: conflito de agenda; ignorada.'
                    )
                    continue
                viagem = Viagem.objects.create(
                    data_hora_partida=partida,
                    rota=rota, motorista=motorista, veiculo=veiculo,
                    status=Viagem.Status.AGENDADA,
                )
                viagem.passageiros.set(pessoas)
                contador['manuais'] += 1

        self.stdout.write(self.style.SUCCESS(
            f'Dados DEMO: {contador["rotas"]} rotas, {contador["veiculos"]} veículos, '
            f'{contador["motoristas"]} motoristas, {contador["passageiros"]} passageiros, '
            f'{contador["programacoes"]} programações e {contador["manuais"]} viagens '
            'avulsas novas.'
        ))
        if not options['sem_gerar']:
            self.stdout.write(self.style.SUCCESS(
                f'Recorrências: {resumo["criadas"]} viagens geradas, '
                f'{resumo["existentes"]} já existentes e {resumo["recusadas"]} recusas.'
            ))
        self.stdout.write('Registros existentes não foram alterados nem apagados.')

    def _rotas(self, contador):
        saida = []
        for nome, origem, destino, km, duracao in ROTAS:
            obj, criado = Rota.objects.get_or_create(
                nome=nome,
                defaults=dict(origem=origem, destino=destino,
                              distancia_km=Decimal(km), duracao_minutos=duracao,
                              observacoes='DADO FICTÍCIO PARA DEMONSTRAÇÃO', ativa=True),
            )
            contador['rotas'] += int(criado)
            saida.append(obj)
        return saida

    def _veiculos(self, contador):
        saida = []
        for placa, marca, modelo, tipo, capacidade in VEICULOS:
            obj, criado = Veiculo.objects.get_or_create(
                placa=placa,
                defaults=dict(marca=marca, modelo=modelo, ano=2024,
                              tipo=tipo, capacidade=capacidade,
                              situacao=Veiculo.Situacao.DISPONIVEL),
            )
            contador['veiculos'] += int(criado)
            saida.append(obj)
        return saida

    def _motoristas(self, contador, fim):
        saida = []
        for i in range(1, 5):
            # CPFs propositalmente inválidos e CNHs fictícias: NÃO são documentos reais.
            cpf, cnh = f'000.000.000-{i:02d}', f'000000000{i:02d}'
            obj, criado = Motorista.objects.get_or_create(
                cpf=cpf,
                defaults=dict(nome=f'Motorista DEMO {i:02d}',
                              data_nascimento=date(1990, 1, 1),
                              cnh_numero=cnh, cnh_categoria='D',
                              cnh_validade=max(fim, timezone.localdate()) + timedelta(days=3650),
                              telefone='00000000000',
                              email=f'motorista-demo-{i}@example.invalid', ativo=True),
            )
            contador['motoristas'] += int(criado)
            saida.append(obj)
        return saida

    def _passageiros(self, contador):
        saida = []
        for i in range(1, 17):
            obj, criado = Passageiro.objects.get_or_create(
                documento=f'DEMO-ALUNO-{i:03d}',
                defaults=dict(nome=f'Passageiro DEMO {i:02d}',
                              telefone='00000000000', ativo=True),
            )
            contador['passageiros'] += int(criado)
            saida.append(obj)
        return saida

    def _programacoes(self, contador, inicio, fim, rotas, veiculos, motoristas, passageiros):
        saida = []
        for nome, i_rota, i_motorista, i_veiculo, grupo, hora in PROGRAMACOES:
            obj, criado = ProgramacaoRecorrente.objects.get_or_create(
                nome=nome,
                defaults=dict(rota=rotas[i_rota], motorista_padrao=motoristas[i_motorista],
                              veiculo_padrao=veiculos[i_veiculo],
                              dias_semana='0,1,2,3,4', hora_partida=hora,
                              data_inicio=inicio, data_fim=fim, ativa=True),
            )
            if criado:
                # Vínculo habitual: os mesmos passageiros participam da ida e volta
                # do seu bairro, independentemente do motorista e do veículo.
                obj.passageiros.set(passageiros[grupo * 8:(grupo + 1) * 8])
            contador['programacoes'] += int(criado)
            saida.append(obj)
        return saida
