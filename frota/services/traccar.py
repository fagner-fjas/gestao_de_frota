import requests
from django.conf import settings

class TraccarError(Exception):
    pass


def traccar_get(endpoint):
    url = (
        settings.TRACCAR_URL.rstrip("/")
        + endpoint
    )

    token = settings.TRACCAR_API_TOKEN

    if not token:
        raise TraccarError(
            "Token de acesso ao Traccar não configurado."
        )

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=10,
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as exc:
        raise TraccarError(
            "Erro ao consultar a API do Traccar."
        ) from exc


def listar_dispositivos():
    return traccar_get("/api/devices")


def ultimas_posicoes():
    return traccar_get("/api/positions")
