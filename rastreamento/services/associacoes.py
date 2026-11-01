"""Associações GPS ↔ veículo, com compatibilidade temporária do mapa legado."""

from django.db import IntegrityError, transaction

from frota.models import Veiculo
from rastreamento.models import DispositivoGPS


class ConflitoAssociacaoGPS(Exception):
    """Vínculo já ocupado ou divergência entre modelo antigo e novo."""


def associar_dispositivo(dispositivo_id, veiculo_id):
    """Define ou remove vínculo; mantém o campo legado sincronizado.

    Uma troca de veículo exige desvinculação explícita antes da nova associação.
    Operação atômica para que a tela legada não fique com vínculo divergente.
    """
    try:
        with transaction.atomic():
            gps = DispositivoGPS.objects.select_for_update().get(pk=dispositivo_id)

            antigo = None
            if gps.veiculo_id is not None:
                antigo = Veiculo.objects.select_for_update().get(pk=gps.veiculo_id)

            novo = None
            if veiculo_id is not None:
                if not gps.ativo:
                    raise ConflitoAssociacaoGPS(
                        'Dispositivo inativo. Reative administrativamente antes de associar.'
                    )
                novo = Veiculo.objects.select_for_update().get(pk=veiculo_id)

                if gps.veiculo_id is not None and gps.veiculo_id != novo.pk:
                    raise ConflitoAssociacaoGPS(
                        'Desvincule o dispositivo do veículo atual antes de transferi-lo.'
                    )

                if (
                    novo.traccar_device_id is not None
                    and novo.traccar_device_id != gps.traccar_id
                ):
                    raise ConflitoAssociacaoGPS(
                        'O veículo possui outro GPS no cadastro legado. Reconcilie antes.'
                    )

                if DispositivoGPS.objects.exclude(pk=gps.pk).filter(veiculo_id=novo.pk).exists():
                    raise ConflitoAssociacaoGPS('O veículo já está vinculado a outro GPS.')

            if antigo is not None and antigo.traccar_device_id not in (None, gps.traccar_id):
                raise ConflitoAssociacaoGPS(
                    'O vínculo legado diverge do cadastro GPS. Reconcilie antes.'
                )

            if antigo is not None and (novo is None or novo.pk != antigo.pk):
                antigo.traccar_device_id = None
                antigo.save(update_fields=['traccar_device_id'])

            gps.veiculo = novo
            gps.save(update_fields=['veiculo', 'atualizado_em'])

            if novo is not None and novo.traccar_device_id != gps.traccar_id:
                novo.traccar_device_id = gps.traccar_id
                novo.save(update_fields=['traccar_device_id'])
    except IntegrityError as exc:
        raise ConflitoAssociacaoGPS(
            'Outro vínculo GPS foi registrado ao mesmo tempo. Atualize a página.'
        ) from exc

    return gps
