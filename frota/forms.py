import re
from datetime import date, timedelta

from django import forms
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .models import Motorista, Passageiro, ProgramacaoRecorrente, Rota, Veiculo, Viagem
from .services.agenda import conflitos_de_agenda


def campo_data():
    return forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})

class RotaForm(forms.ModelForm):
    class Meta:
        model = Rota
        fields = '__all__'
        widgets = {'observacoes': forms.Textarea(attrs={'rows': 3})}


class MotoristaForm(forms.ModelForm):
    class Meta:
        model = Motorista
        fields = '__all__'
        widgets = {
            'data_nascimento': campo_data(),
            'cnh_validade': campo_data(),
        }

    def clean_cpf(self):
        digitos = re.sub(r'\D', '', self.cleaned_data['cpf'])
        if len(digitos) != 11:
            raise forms.ValidationError('O CPF deve ter 11 dígitos.')
        return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'

    def clean_cnh_numero(self):
        numero = self.cleaned_data['cnh_numero'].strip()
        if not re.fullmatch(r'\d{11}', numero):
            raise forms.ValidationError('A CNH deve ter 11 dígitos numéricos.')
        return numero

    def clean_data_nascimento(self):
        nascimento = self.cleaned_data['data_nascimento']
        hoje = date.today()
        aniversario_passou = (hoje.month, hoje.day) >= (nascimento.month, nascimento.day)
        idade = hoje.year - nascimento.year - (0 if aniversario_passou else 1)
        if idade < 18:
            raise forms.ValidationError('O motorista deve ser maior de 18 anos.')
        return nascimento


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        # O campo legado traccar_device_id é mantido exclusivamente pelo
        # serviço de associações até a migração do mapa (Entrega 4).
        fields = [
            'placa', 'marca', 'modelo', 'ano', 'tipo', 'capacidade',
            'quilometragem', 'situacao',
        ]

    def clean_placa(self):
        placa = self.cleaned_data['placa'].upper().replace('-', '').strip()
        # Formato antigo (ABC1234) ou Mercosul (ABC1D23).
        if not re.fullmatch(r'[A-Z]{3}\d[A-Z0-9]\d{2}', placa):
            raise forms.ValidationError('Placa inválida. Use ABC1234 ou ABC1D23.')
        return placa

    def clean_ano(self):
        ano = self.cleaned_data['ano']
        if not 1950 <= ano <= date.today().year:
            raise forms.ValidationError(f'Informe um ano entre 1950 e {date.today().year}.')
        return ano


class PassageiroForm(forms.ModelForm):
    class Meta:
        model = Passageiro
        fields = '__all__'


class SeletorPassageirosWidget(forms.CheckboxSelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        passageiro = getattr(value, 'instance', None)
        if passageiro is not None:
            option['attrs']['data-documento'] = passageiro.documento
            option['attrs']['data-ativo'] = 'true' if passageiro.ativo else 'false'
            option['attrs']['data-vinculado'] = (
                'true' if passageiro.possui_viagem or passageiro.possui_recorrencia else 'false'
            )
        return option


def preparar_seletor_passageiros(campo):
    campo.queryset = campo.queryset.annotate(
        possui_viagem=Exists(
            Viagem.passageiros.through.objects.filter(passageiro_id=OuterRef('pk'))
        ),
        possui_recorrencia=Exists(
            ProgramacaoRecorrente.passageiros.through.objects.filter(passageiro_id=OuterRef('pk'))
        ),
    )


class ViagemForm(forms.ModelForm):
    class Meta:
        model = Viagem
        fields = ['data_hora_partida', 'rota', 'veiculo', 'motorista', 'passageiros']
        widgets = {
            'data_hora_partida': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}
            ),
            'passageiros': SeletorPassageirosWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_hora_partida'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['passageiros'].required = True

        atual = self.instance
        self.fields['rota'].queryset = Rota.objects.filter(Q(ativa=True) | Q(pk=atual.rota_id))
        self.fields['motorista'].queryset = Motorista.objects.filter(
            Q(ativo=True) | Q(pk=atual.motorista_id)
        )
        self.fields['veiculo'].queryset = Veiculo.objects.filter(
            Q(situacao=Veiculo.Situacao.DISPONIVEL) | Q(pk=atual.veiculo_id)
        )
        selecionaveis = Q(ativo=True)
        if self.instance.pk:
            selecionaveis |= Q(pk__in=self.instance.passageiros.values('pk'))
        self.fields['passageiros'].queryset = Passageiro.objects.filter(selecionaveis)
        preparar_seletor_passageiros(self.fields['passageiros'])

    def clean(self):
        dados = super().clean()
        partida = dados.get('data_hora_partida')
        rota = dados.get('rota')
        veiculo = dados.get('veiculo')
        motorista = dados.get('motorista')
        passageiros = dados.get('passageiros')

        mudou_data = not self.instance.pk or 'data_hora_partida' in self.changed_data
        if (partida and self.instance.programacao_recorrente_id
                and self.instance.data_programada
                and timezone.localtime(partida).date() != self.instance.data_programada):
            self.add_error('data_hora_partida', 'A data de uma viagem recorrente não pode ser alterada.')

        if partida and mudou_data and partida < timezone.now():
            self.add_error('data_hora_partida', 'A data e hora de partida não podem estar no passado.')

        if partida and motorista and motorista.cnh_validade < timezone.localtime(partida).date():
            self.add_error('motorista', 'A CNH do motorista estará vencida na data da viagem.')

        if veiculo and passageiros and len(passageiros) > veiculo.capacidade:
            self.add_error(
                'passageiros',
                f'Selecionados {len(passageiros)} passageiros, mas o veículo '
                f'{veiculo.placa} comporta {veiculo.capacidade}.',
            )

        if partida and rota:
            self.verificar_conflitos(partida, rota, veiculo, motorista, passageiros)

        return dados

    def verificar_conflitos(self, partida, rota, veiculo, motorista, passageiros):
        for campo, mensagem in conflitos_de_agenda(
            partida, rota, veiculo, motorista, passageiros, excluir_id=self.instance.pk
        ):
            self.add_error(campo, mensagem)


DIAS_SEMANA = [
    ('0', 'Segunda-feira'), ('1', 'Terça-feira'), ('2', 'Quarta-feira'),
    ('3', 'Quinta-feira'), ('4', 'Sexta-feira'), ('5', 'Sábado'), ('6', 'Domingo'),
]


class ProgramacaoRecorrenteForm(forms.ModelForm):
    dias_semana = forms.MultipleChoiceField(
        choices=DIAS_SEMANA, widget=forms.CheckboxSelectMultiple,
        label='Dias da semana',
    )

    class Meta:
        model = ProgramacaoRecorrente
        fields = [
            'nome', 'rota', 'dias_semana', 'hora_partida', 'data_inicio',
            'data_fim', 'motorista_padrao', 'veiculo_padrao', 'passageiros', 'ativa',
        ]
        widgets = {
            'data_inicio': campo_data(),
            'data_fim': campo_data(),
            'hora_partida': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'passageiros': SeletorPassageirosWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hora_partida'].input_formats = ['%H:%M']
        if self.instance.pk:
            self.initial['dias_semana'] = self.instance.dias_semana.split(',')
        else:
            self.initial['dias_semana'] = ['0', '1', '2', '3', '4']
        self.fields['rota'].queryset = Rota.objects.filter(
            Q(ativa=True) | Q(pk=self.instance.rota_id)
        )
        self.fields['motorista_padrao'].queryset = Motorista.objects.filter(
            Q(ativo=True) | Q(pk=self.instance.motorista_padrao_id)
        )
        self.fields['veiculo_padrao'].queryset = Veiculo.objects.filter(
            Q(situacao=Veiculo.Situacao.DISPONIVEL) | Q(pk=self.instance.veiculo_padrao_id)
        )
        self.fields['passageiros'].queryset = Passageiro.objects.filter(
            Q(ativo=True) | Q(programacaorecorrente=self.instance)
        ).distinct() if self.instance.pk else Passageiro.objects.filter(ativo=True)
        self.fields['passageiros'].required = True
        preparar_seletor_passageiros(self.fields['passageiros'])

    def clean_dias_semana(self):
        dias = self.cleaned_data['dias_semana']
        return ','.join(sorted(dias))

    def clean(self):
        dados = super().clean()
        veiculo = dados.get('veiculo_padrao')
        passageiros = dados.get('passageiros')
        motorista = dados.get('motorista_padrao')
        inicio = dados.get('data_inicio')
        fim = dados.get('data_fim')
        if veiculo and passageiros and len(passageiros) > veiculo.capacidade:
            self.add_error('passageiros', 'Passageiros acima da capacidade do veículo padrão.')
        if motorista and inicio and motorista.cnh_validade < inicio:
            self.add_error('motorista_padrao', 'CNH vencida na data de início.')
        if inicio and fim and fim < inicio:
            self.add_error('data_fim', 'A data final não pode ser anterior à inicial.')
        return dados


class ConfirmacaoEmbarqueForm(forms.Form):
    motorista = forms.ModelChoiceField(queryset=Motorista.objects.none())
    veiculo = forms.ModelChoiceField(queryset=Veiculo.objects.none(), label='Veículo utilizado')
    passageiros_embarcados = forms.IntegerField(min_value=0, label='Passageiros embarcados')

    def __init__(self, *args, viagem, **kwargs):
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        self.fields['motorista'].queryset = Motorista.objects.filter(
            Q(ativo=True) | Q(pk=viagem.motorista_id)
        )
        self.fields['veiculo'].queryset = Veiculo.objects.filter(
            Q(situacao=Veiculo.Situacao.DISPONIVEL) | Q(pk=viagem.veiculo_id)
        )
        self.initial.update({
            'motorista': viagem.motorista_id,
            'veiculo': viagem.veiculo_id,
            'passageiros_embarcados': viagem.passageiros.count(),
        })

    def clean(self):
        dados = super().clean()
        motorista = dados.get('motorista')
        veiculo = dados.get('veiculo')
        total = dados.get('passageiros_embarcados')
        partida = self.viagem.data_hora_partida
        if total is not None and veiculo and total > veiculo.capacidade:
            self.add_error('passageiros_embarcados', 'A contagem excede a capacidade do veículo.')
        if motorista and not motorista.ativo:
            self.add_error('motorista', 'Motorista inativo.')
        if veiculo and veiculo.situacao != Veiculo.Situacao.DISPONIVEL:
            self.add_error('veiculo', 'Veículo indisponível para confirmação.')
        if motorista and motorista.cnh_validade < timezone.localtime(partida).date():
            self.add_error('motorista', 'CNH vencida para esta viagem.')
        if motorista and veiculo:
            for campo, mensagem in conflitos_de_agenda(
                partida, self.viagem.rota, veiculo, motorista,
                self.viagem.passageiros.all(), excluir_id=self.viagem.pk,
            ):
                if campo in ('motorista', 'veiculo'):
                    self.add_error(campo, mensagem)
                else:
                    self.add_error(None, mensagem)
        return dados
