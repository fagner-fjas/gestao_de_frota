from django.db import IntegrityError, transaction

from .client import TraccarResponseError
from .dispositivos import listar_dispositivos
from rastreamento.models import DispositivoGPS


class SincronizacaoGPSInvalida(Exception):
    """"""


def _normalizar(dispositivos):
    resultado = []
    ids = set()
    identificadores = set()

    for item in dispositivos:
        identificador = item.get('id')
        nome = item.get('name')
        unique_id = item.get('uniqueId')
        if (
            type(identificador) is not int or identificador <= 0
            or not isinstance(nome, str) or not nome.strip()
            or not isinstance(unique_id, str) or not unique_id.strip()
            or len(unique_id.strip()) > 128
        ):
            raise TraccarResponseError('Traccar retornou identificação de GPS inválida.')

        unique_id = unique_id.strip()
        if identificador in ids or unique_id in identificadores:
            raise TraccarResponseError('Traccar retornou dispositivos duplicados.')
        ids.add(identificador)
        identificadores.add(unique_id)
        resultado.append((identificador, nome.strip()[:120], unique_id))

    return resultado


def sincronizar_dispositivos():
    """Importa dispositivos; retorna contagens de criados e atualizados.

    Não remove registros ausentes na API. Uma falha no meio da sincronização
    desfaz todas as alterações locais nesta execução.
    """
    dados = _normalizar(listar_dispositivos())
    criados = 0
    atualizados = 0

    try:
        with transaction.atomic():
            for traccar_id, nome, unique_id in dados:
                dispositivo = (
                    DispositivoGPS.objects.select_for_update()
                    .filter(traccar_id=traccar_id)
                    .first()
                )
                if dispositivo is None:
                    DispositivoGPS.objects.create(
                        traccar_id=traccar_id,
                        nome=nome,
                        unique_id=unique_id,
                    )
                    criados += 1
                    continue

                if dispositivo.unique_id and dispositivo.unique_id != unique_id:
                    raise SincronizacaoGPSInvalida(
                        f'Identificador divergente para o GPS Traccar #{traccar_id}. '
                        'Verifique o dispositivo antes de sincronizar.'
                    )

                campos_alterados = []
                if not dispositivo.unique_id:
                    dispositivo.unique_id = unique_id
                    campos_alterados.append('unique_id')

                # Apenas os nomes provisórios da migração recebem nome remoto.
                if dispositivo.nome == f'GPS Traccar #{traccar_id} (migrado)':
                    dispositivo.nome = nome
                    campos_alterados.append('nome')

                if campos_alterados:
                    dispositivo.save(update_fields=campos_alterados + ['atualizado_em'])
                    atualizados += 1
    except IntegrityError as exc:
        raise SincronizacaoGPSInvalida(
            'Conflito de identificadores GPS no banco local. Nenhum registro foi importado.'
        ) from exc

    return {'criados': criados, 'atualizados': atualizados}
