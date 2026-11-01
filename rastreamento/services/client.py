import logging
from urllib.parse import urlsplit

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


TIMEOUT = (3.05, 7)


class TraccarError(Exception):
    """Erro público da integração com Traccar."""


class TraccarConfigError(TraccarError):
    """Configuração local ausente ou inválida."""


class TraccarAuthError(TraccarError):
    """O servidor rejeitou as credenciais da integração."""


class TraccarUnavailableError(TraccarError):
    """Servidor inacessível, timeout ou indisponibilidade temporária."""


class TraccarResponseError(TraccarError):
    """Resposta inesperada, inválida ou incompatível com a API."""


def traccar_get(endpoint):
    """endpoint .

    Comentario trocar burro.
    """
    if not isinstance(endpoint, str) or not endpoint.startswith('/api/'):
        raise ValueError('Endpoint Traccar inválido.')
    path = urlsplit(endpoint)
    if path.scheme or path.netloc or path.fragment or not path.path.startswith('/api/'):
        raise ValueError('Endpoint Traccar inválido.')

    base_url = str(getattr(settings, 'TRACCAR_URL', '') or '').strip().rstrip('/')
    token = str(getattr(settings, 'TRACCAR_API_TOKEN', '') or '').strip()
    if not token or not base_url or urlsplit(base_url).scheme not in ('http', 'https'):
        raise TraccarConfigError('Configuração de acesso ao Traccar incompleta.')

    try:
        response = requests.get(
            base_url + endpoint,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            },
            timeout=TIMEOUT,
            allow_redirects=False,
        )
    except requests.Timeout as exc:
        logger.warning('Timeout na comunicação com o Traccar.')
        raise TraccarUnavailableError('Tempo limite ao consultar o Traccar.') from exc
    except requests.RequestException as exc:
        logger.warning('Falha de conexão com a API Traccar.')
        raise TraccarUnavailableError('Não foi possível conectar ao Traccar.') from exc

    status = response.status_code
    if status in (401, 403):
        logger.warning('Autenticação Traccar recusada (HTTP %s).', status)
        raise TraccarAuthError('Acesso ao Traccar não autorizado.')
    if status in (429, 502, 503, 504) or status >= 500:
        logger.warning('Traccar temporariamente indisponível (HTTP %s).', status)
        raise TraccarUnavailableError('Traccar temporariamente indisponível.')
    if not 200 <= status < 300:
        logger.warning('Resposta inesperada do Traccar (HTTP %s).', status)
        raise TraccarResponseError('Traccar retornou uma resposta inesperada.')

    try:
        return response.json()
    except ValueError as exc:
        logger.warning('Traccar retornou JSON inválido.')
        raise TraccarResponseError('Traccar retornou dados inválidos.') from exc


def traccar_get_collection(endpoint, required_keys):
    """Consulta uma coleção JSON, sem mascarar payloads malformados.

    A validação é mínima: o serviço de domínio valida campos adicionais.
    """
    rows = traccar_get(endpoint)
    if not isinstance(rows, list):
        raise TraccarResponseError('Traccar não retornou uma lista de dados.')
    for item in rows:
        if not isinstance(item, dict) or not all(key in item for key in required_keys):
            raise TraccarResponseError('Traccar retornou registros incompletos.')
    return rows
