# ADR-0001 — Separação do rastreamento em app Django

- **Status:** aceita para o MVP; implementação incremental
- **Data:** 2026-10-31
- **Fonte:** revisão do `gestao_de_frota_atual(1).zip`

## Contexto

O app `frota` contém `Veiculo`, `Rota`, `Motorista`, `Passageiro` e `Viagem`. A integração inicial usa `Veiculo.traccar_device_id`, `frota/services/traccar.py`, `frota/views_rastreamento.py` e o mapa Leaflet independente do layout principal. O Traccar gerencia os dispositivos e as posições.

## Decisão

Criar `rastreamento`, app Django no **mesmo** projeto `projeto_mvp` e banco MySQL, com modelo `DispositivoGPS` e associação opcional `OneToOneField` a `frota.Veiculo`. O Traccar continua fonte de verdade para dispositivo e telemetria. O Django guarda vínculo e metadados; não armazena uma cópia do histórico GPS.

## Limites e evolução

- Etapa 1: criar modelo e copiar associações legadas, **sem** remover campo `Veiculo.traccar_device_id`.
- Etapa 2: separar cliente HTTP/serviço, validar esquemas e tratar erros com testes, mantendo endpoints antigos até migração.
- Etapa 3: importar/sincronizar dispositivos existentes pela API, configurar permissões e oferecer operações administrativas dedicadas. Neste estágio, `DispositivoGPSAdmin` é intencionalmente somente leitura.
- Etapa 4: mapa de veículos com atualização visual de 60 s, timestamp real e estados de posição recente/antiga/ausente.
- Etapa 5: mapa compacto no dashboard, reutilizando layout TailAdmin.
- Relatórios históricos não fazem parte do escopo atual.

## Invariantes

1. Um veículo tem zero ou um GPS; GPS tem zero ou um veículo.
2. `traccar_id` e `unique_id` (quando conhecido) são únicos.
3. `unique_id = NULL` indica dispositivo importado apenas do vínculo legado, aguardando reconciliação.
4. Apagar um veículo não apaga o dispositivo Traccar (o vínculo é desfeito).
5. O dispositivo online pode ter uma posição antiga; estado de conexão e idade do posicionamento são informações independentes.
6. Consultas a posições ficam no servidor Django, autenticadas e autorizadas; nunca expor token Traccar no navegador.
7. Não excluir migrações legadas ou executar `docker compose down -v` como parte desta implementação.

## Alternativas rejeitadas

- Continuar usando somente `Veiculo.traccar_device_id`: não permite gestão de GPS sem associação.
- Criar outro microsserviço Django: custo operacional maior sem necessidade neste MVP.
- Salvar cada posição no MySQL administrativo: duplicação de dados da fonte Traccar.

## Risco conhecido

Durante a transição, há **duas representações do mesmo vínculo**. Não permitir edição do novo vínculo antes de refatorar as leituras e remover o campo legado em uma entrega posterior. Fazer backup e validar contagem e correspondência dos registros após a migração.
