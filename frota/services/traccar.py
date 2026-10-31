"""Adaptador legado: evita quebrar as views existentes durante a refatoração.

Novos recursos devem importar diretamente de `rastreamento.services`.
Este módulo será removido somente após migrarmos a view do mapa.
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
