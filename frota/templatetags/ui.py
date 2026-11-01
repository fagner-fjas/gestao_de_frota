from django import forms, template

register = template.Library()

BADGES = {
    'Agendada': 'bg-brand-50 text-brand-500',
    'Em andamento': 'bg-warning-50 text-warning-600',
    'Concluída': 'bg-success-50 text-success-600',
    'Cancelada': 'bg-error-50 text-error-600',
    'Disponível': 'bg-success-50 text-success-600',
    'Em viagem': 'bg-brand-50 text-brand-500',
    'Em manutenção': 'bg-warning-50 text-warning-600',
    'Inativo': 'bg-gray-100 text-gray-600',
    'Sim': 'bg-success-50 text-success-600',
    'Não': 'bg-gray-100 text-gray-600',
}


@register.filter
def badge(valor):
    return BADGES.get(str(valor), '')


@register.filter
def estilizar(campo):
    widget = campo.field.widget
    if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
        return campo
    classe = 'campo-area' if isinstance(widget, forms.Textarea) else 'campo'
    existente = widget.attrs.get('class', '')
    return campo.as_widget(attrs={'class': f'{existente} {classe}'.strip()})