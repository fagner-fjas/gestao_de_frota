# Entrega 4 — Mapa da Frota integrado ao TailAdmin

## Objetivo

Visualizar a última posição conhecida de cada veículo associado a um GPS administrativamente ativo, com atualização do dashboard a cada 60 segundos, sem modificar a base de dados.

## Estrutura de código

- `rastreamento/services/monitoramento.py`: caso de uso, leitura de vínculos, enriquecimento e classificação do tempo da posição.
- `rastreamento/views_mapa.py`: endpoints Django GET com autenticação, permissão e tratamento de falha remota.
- `rastreamento/urls.py`: preserva `/rastreamento/` e `/rastreamento/dados/` e seus `name`s.
- `rastreamento/templates/rastreamento/mapa.html`: renderização com `base.html`/TailAdmin.
- `assets/rastreamento/mapa.js` e `mapa.css`: Leaflet, atualização, tabela/lista, popups e aviso de falha.
- `rastreamento/tests_mapa.py`: testes do caso de uso, autorização, endpoint e erros.
- Removidos: `frota/views_rastreamento.py` e `templates/frota/rastreamento.html` (código legado de apresentação; os dados do banco não são removidos).

## Contrato do endpoint

`GET /rastreamento/dados/` (login + `rastreamento.view_dispositivogps`). Exemplo fictício:

```json
{
  "consultado_em": "2026-10-31T16:00:00+00:00",
  "resumo": {
    "total_vinculados": 1,
    "com_posicao": 1,
    "recentes": 1,
    "atrasadas": 0,
    "desatualizadas": 0,
    "sem_horario": 0,
    "sem_posicao": 0
  },
  "veiculos": [{
    "id": 1,
    "placa": "ABC1D23",
    "modelo": "Kombi",
    "gps_nome": "GPS exemplo",
    "traccar_id": 19,
    "latitude": -7.67,
    "longitude": -36.88,
    "horario": "2026-10-31T15:59:40Z",
    "idade_segundos": 20,
    "estado_localizacao": "recente",
    "status_dispositivo": "online",
    "velocidade_kmh": 18.5,
    "bateria": 72.0
  }]
}
```

`bateria` e `velocidade_kmh` são opcionais (nulos se ausentes ou inválidos). `status_dispositivo` não substitui `estado_localizacao`. Quando não há posição, coordenadas e horário são nulos; o veículo permanece listado.

Em falhas Traccar: status HTTP **503** com `{"erro": "Não foi possível atualizar as posições GPS."}`. Nenhum dado fictício é gerado.

## Como aplicar no Linux Mint

1. Estar em uma branch de trabalho, com `git status` limpo ou mudanças preservadas em commit; manter backup existente do MySQL/Traccar.
2. Na raiz do projeto, baixar `entrega_04_mapa_frota.patch` para `~/Downloads`.
3. Executar:

```bash
git apply --check "$HOME/Downloads/entrega_04_mapa_frota.patch"
git apply "$HOME/Downloads/entrega_04_mapa_frota.patch"
git diff --check
sudo docker compose exec web python manage.py check
sudo docker compose exec web python manage.py makemigrations --check --dry-run
sudo docker compose exec web python manage.py test rastreamento -v 2
sudo docker compose exec web python manage.py test frota usuarios rastreamento -v 2
```

4. Atribuir **view_dispositivogps** aos gestores que precisam consultar mapa e posições. Superusuários possuem permissão automaticamente.
5. Abrir `http://localhost:8000/rastreamento/`, com uma conta autorizada, e `http://localhost:8000/rastreamento/dados/`.
6. Confirmar que os dispositivos vinculados em `/gps/` aparecem. O dispositivo **não vinculado** não deve aparecer como veículo.
7. Desconectar temporariamente **seu próprio dispositivo de teste** para validar a indicação de dados antigos/sem comunicação (sem mudar dados de terceiros).

## Critérios de aceite

- A rota do mapa exibe `base.html` e sidebar TailAdmin.
- As duas URLs antigas continuam acessíveis com os mesmos nomes Django.
- O JSON utiliza somente `DispositivoGPS.veiculo`; `Veiculo.traccar_device_id` não participa da consulta.
- Indicadores distinguem recentes (<= 90 s), atrasadas (<= 180 s), antigas (> 180 s), sem horário e sem posição.
- Velocidade converte nós em km/h (`* 1.852`) e bateria aparece apenas quando presente na telemetria.
- Atualização visual a cada **60.000 ms**, sem forçar recentralização a cada consulta.
- Acesso negado a usuário sem permissão de GPS, mesmo que ele tenha permissão de leitura de veículos.
- Com Traccar indisponível, HTTP 503 e aviso claro na interface; sem posições falsas.
- Sem migrações novas e sem dependências adicionais.

## Nota de segurança

O ZIP original inclui `.env` e `.git`, que não foram incluídos nos artefatos desta entrega. Proteja credenciais e não compartilhe tokens do Traccar. O servidor web e a API não devem ficar publicamente acessíveis sem proteção adicional.
