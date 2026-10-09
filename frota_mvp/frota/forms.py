import re
from datetime import date, timedelta

from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import Motorista, Passageiro, Rota, Veiculo, Viagem


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
        fields = '__all__'

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


class ViagemForm(forms.ModelForm):
    class Meta:
        model = Viagem
        fields = ['data_hora_partida', 'rota', 'veiculo', 'motorista', 'passageiros']
        widgets = {
            'data_hora_partida': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}
            ),
            'passageiros': forms.CheckboxSelectMultiple,
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
        self.fields['passageiros'].queryset = Passageiro.objects.filter(ativo=True)

    def clean(self):
        dados = super().clean()
        partida = dados.get('data_hora_partida')
        rota = dados.get('rota')
        veiculo = dados.get('veiculo')
        motorista = dados.get('motorista')
        passageiros = dados.get('passageiros')

        mudou_data = not self.instance.pk or 'data_hora_partida' in self.changed_data
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
        fim = partida + timedelta(minutes=rota.duracao_minutos)

        filtro = Q()
        if veiculo:
            filtro |= Q(veiculo=veiculo)
        if motorista:
            filtro |= Q(motorista=motorista)
        if passageiros:
            filtro |= Q(passageiros__in=passageiros)
        if not filtro:
            return

        outras = Viagem.objects.filter(
            status__in=[Viagem.Status.AGENDADA, Viagem.Status.EM_ANDAMENTO]
        ).select_related('rota').prefetch_related('passageiros')
        if self.instance.pk:
            outras = outras.exclude(pk=self.instance.pk)

        ids_selecionados = {p.pk for p in passageiros or []}
        for outra in outras.filter(filtro).distinct():
            outra_fim = outra.data_hora_partida + timedelta(minutes=outra.rota.duracao_minutos)
            if not (partida < outra_fim and outra.data_hora_partida < fim):
                continue  

            referencia = f'viagem #{outra.pk} ({outra})'
            if veiculo and outra.veiculo_id == veiculo.pk:
                self.add_error('veiculo', f'Veículo já alocado na {referencia}.')
            if motorista and outra.motorista_id == motorista.pk:
                self.add_error('motorista', f'Motorista já alocado na {referencia}.')
            em_conflito = [p.nome for p in outra.passageiros.all() if p.pk in ids_selecionados]
            if em_conflito:
                self.add_error(
                    'passageiros',
                    f'Passageiro(s) já em outra viagem no mesmo período: '
                    f'{", ".join(em_conflito)} ({referencia}).',
                )
