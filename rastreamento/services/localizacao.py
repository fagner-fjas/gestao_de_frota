"""Consulta das últimas posições disponíveis, sem persistência no Django."""

from math import isfinite

from .client import TraccarResponseError, traccar_get_collection


def ultimas_posicoes():
    """Últimas posições conhecidas (não necessariamente atuais)."""
    posicoes = traccar_get_collection(
        '/api/positions', ('deviceId', 'latitude', 'longitude')
    )
    for posicao in posicoes:
        device_id = posicao['deviceId']
        lat, lon = posicao['latitude'], posicao['longitude']
        if type(device_id) is not int or device_id <= 0:
            raise TraccarResponseError('Traccar retornou ID de posição inválido.')
        if (
            type(lat) not in (int, float) or type(lon) not in (int, float)
            or not isfinite(lat) or not isfinite(lon)
            or not -90 <= lat <= 90 or not -180 <= lon <= 180
        ):
            raise TraccarResponseError('Traccar retornou coordenadas inválidas.')
    return posicoes
