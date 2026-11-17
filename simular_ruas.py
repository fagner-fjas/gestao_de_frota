
import json
import math
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TRACCAR = "http://192.168.1.227:5055/"
DISPOSITIVO = "CARRO-SB-001"

INTERVALO = 2  

# Coordenadas aproximadas na área urbana de Serra Branca-PB
# Ordem: longitude, latitude
PARADAS = [
    (-36.6660, -7.4803),
    (-36.6646, -7.4790),
    (-36.6631, -7.4812),
]

def distancia(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 6371000 * 2 * math.asin(math.sqrt(h))


def buscar_rota():
    caminho = ";".join(
        f"{lon},{lat}" for lon, lat in PARADAS
    )

    url = (
        "https://router.project-osrm.org"
        f"/route/v1/driving/{caminho}"
        "?overview=full&geometries=geojson"
    )

    print("Buscando ruas no OpenStreetMap...")

    req = Request(
        url,
        headers={"User-Agent": "SimuladorGPS-Estudo/1.0"}
    )

    with urlopen(req, timeout=30) as resposta:
        dados = json.load(resposta)

    if dados.get("code") != "Ok":
        raise RuntimeError(
            f"Não foi possível calcular a rota: {dados}"
        )


    rota = dados["routes"][0]
    if rota["distance"] > 10000:
        raise RuntimeError(
            "Rota superior a 10 km. Revise as paradas."
        )

    return rota


def gerar_posicoes(coordenadas, distancia_total):
    passo = max(10, distancia_total / 120)

    pontos = []

    for a, b in zip(coordenadas, coordenadas[1:]):
        lon1, lat1 = a
        lon2, lat2 = b

        metros = distancia((lat1, lon1), (lat2, lon2))
        divisoes = max(1, math.ceil(metros / passo))

        for i in range(divisoes):
            t = i / divisoes

            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t

            pontos.append((lat, lon))

    lon, lat = coordenadas[-1]
    pontos.append((lat, lon))

    return pontos


def enviar_posicao(lat, lon, velocidade):
    parametros = urlencode({
        "id": DISPOSITIVO,
        "lat": f"{lat:.7f}",
        "lon": f"{lon:.7f}",
        "timestamp": int(time.time()),
        "speed": f"{velocidade:.2f}",
        "valid": "true",
    })

    with urlopen(
        TRACCAR + "?" + parametros,
        timeout=10
    ) as resposta:
        if resposta.status != 200:
            raise RuntimeError(
                f"Traccar retornou HTTP {resposta.status}"
            )


def main():
    rota = buscar_rota()

    coordenadas = rota["geometry"]["coordinates"]
    distancia_total = rota["distance"]

    pontos = gerar_posicoes(
        coordenadas, distancia_total
    )

    print(f"Rota calculada: {distancia_total:.0f} metros")
    print(f"Posições: {len(pontos)}")
    print("Iniciando carro simulado...\n")

    anterior = None

    for i, atual in enumerate(pontos, start=1):
        velocidade = 0

        if anterior is not None:
            metros = distancia(anterior, atual)
            metros_segundo = metros / INTERVALO

            velocidade = metros_segundo * 1.94384

        lat, lon = atual
        enviar_posicao(lat, lon, velocidade)

        print(
            f"[{i}/{len(pontos)}] "
            f"Lat: {lat:.6f} | "
            f"Lon: {lon:.6f} | "
            f"{velocidade * 1.852:.1f} km/h"
        )

        anterior = atual

        if i < len(pontos):
            time.sleep(INTERVALO)

    print("\nTrajeto concluído!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulação interrompida.")
    except Exception as erro:
        print(f"\nErro: {erro}")
