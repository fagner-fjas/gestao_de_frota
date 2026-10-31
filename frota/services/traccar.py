"""Adaptador temporário para imports antigos da API Traccar.

O mapa usa diretamente `rastreamento.services` desde a Entrega 4.
Esta compatibilidade é mantida para outros consumidores e testes legados.
"""

from rastreamento.services.client import (
    TraccarError,
    TraccarConfigError,
    TraccarAuthError,
    TraccarUnavailableError,
    TraccarResponseError,
    traccar_get,
)
from rastreamento.services.dispositivos import listar_dispositivos
from rastreamento.services.localizacao import ultimas_posicoes

__all__ = (
    'TraccarError',
    'TraccarConfigError',
    'TraccarAuthError',
    'TraccarUnavailableError',
    'TraccarResponseError',
    'traccar_get',
    'listar_dispositivos',
    'ultimas_posicoes',
)
