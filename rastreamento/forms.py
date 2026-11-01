"""Formulários administrativos do módulo GPS."""

from django import forms

from frota.models import Veiculo


class AssociacaoGPSForm(forms.Form):
    veiculo = forms.ModelChoiceField(
        label='Veículo associado',
        queryset=Veiculo.objects.none(),
        required=False,
        empty_label='Nenhum — GPS disponível',
        widget=forms.Select(attrs={'class': 'campo'}),
    )

    def __init__(self, *args, dispositivo, **kwargs):
        super().__init__(*args, **kwargs)
        # Não oferecer veículos vinculados a outros GPS; a camada de serviço
        # também verifica o conflito, inclusive em requisições concorrentes.
        livres = Veiculo.objects.filter(dispositivo_gps__isnull=True)
        if dispositivo.veiculo_id is not None:
            livres = Veiculo.objects.filter(
                pk=dispositivo.veiculo_id
            ) | livres
        self.fields['veiculo'].queryset = livres.order_by('placa')
        self.fields['veiculo'].initial = dispositivo.veiculo_id
