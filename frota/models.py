from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Rota(models.Model):
    nome = models.CharField('nome / código', max_length=100, unique=True)
    origem = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    distancia_km = models.DecimalField(
        'distância (km)', max_digits=7, decimal_places=1,
        validators=[MinValueValidator(Decimal('0.1'))],
    )
    duracao_minutos = models.PositiveIntegerField(
        'duração (minutos)', validators=[MinValueValidator(1)],
    )
    observacoes = models.TextField('observações', blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'rota'
        verbose_name_plural = 'rotas'

    def __str__(self):
        return f'{self.nome} ({self.origem} → {self.destino})'


class Motorista(models.Model):
    class CategoriaCNH(models.TextChoices):
        A = 'A', 'A'
        B = 'B', 'B'
        C = 'C', 'C'
        D = 'D', 'D'
        E = 'E', 'E'

    nome = models.CharField('nome completo', max_length=150)
    cpf = models.CharField('CPF', max_length=14, unique=True)
    data_nascimento = models.DateField('data de nascimento')
    cnh_numero = models.CharField('Nº da CNH', max_length=11, unique=True)
    cnh_categoria = models.CharField('categoria da CNH', max_length=1, choices=CategoriaCNH.choices)
    cnh_validade = models.DateField('validade da CNH')
    telefone = models.CharField(max_length=20)
    email = models.EmailField('e-mail', blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'motorista'
        verbose_name_plural = 'motoristas'

    def clean(self):
        if self.cnh_validade and self.cnh_validade < timezone.localdate():
            raise ValidationError({'cnh_validade': 'CNH vencida.'})

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    class Tipo(models.TextChoices):
        CARRO = 'CARRO', 'Carro'
        VAN = 'VAN', 'Van'
        MICROONIBUS = 'MICROONIBUS', 'Micro-ônibus'
        ONIBUS = 'ONIBUS', 'Ônibus'
        CAMINHAO = 'CAMINHAO', 'Caminhão'

    class Situacao(models.TextChoices):
        DISPONIVEL = 'DISPONIVEL', 'Disponível'
        EM_VIAGEM = 'EM_VIAGEM', 'Em viagem'
        MANUTENCAO = 'MANUTENCAO', 'Em manutenção'
        INATIVO = 'INATIVO', 'Inativo'

    placa = models.CharField(max_length=8, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    ano = models.PositiveIntegerField('ano de fabricação')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    capacidade = models.PositiveIntegerField(
        'capacidade de passageiros', validators=[MinValueValidator(1)],
    )
    quilometragem = models.PositiveIntegerField('quilometragem atual', default=0)
    situacao = models.CharField(
        'situação', max_length=20, choices=Situacao.choices, default=Situacao.DISPONIVEL,
    )

    class Meta:
        ordering = ['placa']
        verbose_name = 'veículo'
        verbose_name_plural = 'veículos'

    def __str__(self):
        return f'{self.placa} - {self.modelo}'


class Passageiro(models.Model):
    nome = models.CharField('nome completo', max_length=150)
    documento = models.CharField('CPF / documento', max_length=20, unique=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField('e-mail', blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'passageiro'
        verbose_name_plural = 'passageiros'

    def __str__(self):
        return self.nome


class Viagem(models.Model):
    class Status(models.TextChoices):
        AGENDADA = 'AGENDADA', 'Agendada'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'
        CANCELADA = 'CANCELADA', 'Cancelada'

    data_hora_partida = models.DateTimeField('data e hora de partida', db_index=True)
    rota = models.ForeignKey(Rota, on_delete=models.PROTECT)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, verbose_name='veículo')
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT)
    passageiros = models.ManyToManyField(Passageiro, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AGENDADA, db_index=True,
    )

    class Meta:
        ordering = ['data_hora_partida']
        verbose_name = 'viagem'
        verbose_name_plural = 'viagens'

    @property
    def total_passageiros(self):
        return len(self.passageiros.all())

    @property
    def passageiros_texto(self):
        return ', '.join(p.nome for p in self.passageiros.all())

    def __str__(self):
        partida = timezone.localtime(self.data_hora_partida)
        return f'{self.rota.nome} em {partida:%d/%m/%Y %H:%M}'
