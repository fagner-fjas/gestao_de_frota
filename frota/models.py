from decimal import Decimal

<<<<<<< HEAD
=======
from django.conf import settings
>>>>>>> paineis
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

    traccar_device_id = models.PositiveIntegerField(
        "ID do dispositivo Traccar",
        null=True,
        blank=True,
        unique=True,
        )

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


<<<<<<< HEAD
=======

class ProgramacaoRecorrente(models.Model):
    """Regra de recorrência. Cada data materializada será uma Viagem independente."""

    nome = models.CharField(max_length=120)
    rota = models.ForeignKey(Rota, on_delete=models.PROTECT)
    motorista_padrao = models.ForeignKey(
        Motorista, on_delete=models.PROTECT, related_name='programacoes_padrao'
    )
    veiculo_padrao = models.ForeignKey(
        Veiculo, on_delete=models.PROTECT, related_name='programacoes_padrao'
    )
    passageiros = models.ManyToManyField(Passageiro, blank=True)
    # Segunda-feira = 0, domingo = 6. Exemplo: "0,1,2,3,4".
    dias_semana = models.CharField(max_length=13)
    hora_partida = models.TimeField()
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome', 'id']
        verbose_name = 'programação recorrente'
        verbose_name_plural = 'programações recorrentes'

    def clean(self):
        super().clean()
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'A data final deve ser posterior à inicial.'})
        try:
            dias = [int(item) for item in self.dias_semana.split(',')]
        except (ValueError, AttributeError):
            dias = []
        if not dias or len(set(dias)) != len(dias) or not set(dias).issubset(set(range(7))):
            raise ValidationError({'dias_semana': 'Escolha dias válidos, sem repetições.'})

    def __str__(self):
        return self.nome

    # Os identificadores numéricos são mantidos no banco e usados pela lógica de geração.
    # Somente a camada de apresentação deve exibir os nomes dos dias.
    DIAS_EXTENSO = (
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
        'Sexta-feira', 'Sábado', 'Domingo',
    )
    DIAS_ABREVIADOS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')

    @property
    def dias_semana_indices(self):
        """Retorna os dias normalizados e ordenados, sem consultar o banco."""
        try:
            dias = [int(parte.strip()) for parte in self.dias_semana.split(',')]
        except (AttributeError, ValueError):
            return ()
        if not dias or len(dias) != len(set(dias)) or any(d < 0 or d > 6 for d in dias):
            return ()
        return tuple(sorted(dias))

    @property
    def dias_semana_por_extenso(self):
        """Ex.: 'Segunda-feira, Terça-feira, Quarta-feira'."""
        return ', '.join(self.DIAS_EXTENSO[d] for d in self.dias_semana_indices) or '—'

    @property
    def dias_semana_resumidos(self):
        """Ex.: 'Seg, Ter, Qua' para listagens compactas."""
        return ', '.join(self.DIAS_ABREVIADOS[d] for d in self.dias_semana_indices) or '—'


>>>>>>> paineis
class Viagem(models.Model):
    class Status(models.TextChoices):
        AGENDADA = 'AGENDADA', 'Agendada'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'
        CANCELADA = 'CANCELADA', 'Cancelada'

<<<<<<< HEAD
=======
    programacao_recorrente = models.ForeignKey(
        ProgramacaoRecorrente, null=True, blank=True,
        on_delete=models.PROTECT, related_name='viagens',
    )
    data_programada = models.DateField(null=True, blank=True)
    passageiros_embarcados = models.PositiveIntegerField(null=True, blank=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='viagens_confirmadas',
    )
>>>>>>> paineis
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
<<<<<<< HEAD
=======
        constraints = [models.UniqueConstraint(
            fields=['programacao_recorrente', 'data_programada'],
            name='unica_viagem_por_programacao_data',
        )]
>>>>>>> paineis

    @property
    def total_passageiros(self):
        return len(self.passageiros.all())

    @property
    def passageiros_texto(self):
        return ', '.join(p.nome for p in self.passageiros.all())

    def __str__(self):
        partida = timezone.localtime(self.data_hora_partida)
        return f'{self.rota.nome} em {partida:%d/%m/%Y %H:%M}'
