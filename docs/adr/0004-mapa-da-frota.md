# ADR-0004 — Monitoramento GPS da frota no app `rastreamento`

- **Status:** proposto/implementado no patch da Entrega 4; aguardando testes Django no ambiente do desenvolvedor
- **Data:** 2026-10-31
- **Base:** `gestao_de_frota_passo3.zip` (Entrega 3; 39 testes reportados como aprovados)

## Contexto

O MVP já possui `DispositivoGPS` e a associação administrativa atômica a `Veiculo`, mas `/rastreamento/` ainda é uma view antiga em `frota`, renderizada fora do TailAdmin e baseada no campo legado `Veiculo.traccar_device_id`. O projeto também possui cliente Traccar HTTP tipado (`rastreamento.services`).

## Decisões

1. **Fronteira de domínio:** a nova view fica em `rastreamento/views_mapa.py`; o caso de uso em `rastreamento/services/monitoramento.py`. URLs públicas e nomes anteriores ficam iguais; rotas saem de `frota/urls.py` e passam a `rastreamento/urls.py`.
2. **Associação única:** para exibir um veículo no monitoramento, a fonte é `DispositivoGPS.veiculo`, não o campo `traccar_device_id` do veículo. Somente dispositivos associados e `ativo=True` entram no mapa. Dispositivos não associados não representam veículos no painel.
3. **Dois sistemas distintos:** Django armazena vínculos; Traccar fornece a última posição conhecida. Nenhuma posição é salva no MySQL Django.
4. **Disponibilidade:** o backend realiza no máximo duas consultas por atualização (`GET /api/devices`, `GET /api/positions`) e indexa dispositivos/posições pelo ID; não executa uma requisição por ônibus. Sem veículos vinculados, não consulta o Traccar.
5. **Sem posição também aparece:** o JSON traz todos os veículos monitorados, mesmo sem coordenadas, para que a lista administrativa informe ausência de dados.
6. **Frescor separado de conexão:** um Traccar `online` não garante GPS recente. Idade calculada pelo `fixTime` em relação ao relógio do servidor; até 90 segundos = recente, 91–180 = atrasada, mais de 180 = desatualizada. Sem `fixTime` interpretável, sinalizar `sem_horario` sem afirmar que está recente. O relógio do dispositivo muito adiantado (mais de 60 s) também gera `sem_horario`.
7. **60 segundos = frequência da interface:** `GET /rastreamento/dados/` a cada 60 segundos enquanto a página estiver aberta. Isso **não configura os intervalos de envio do equipamento**, os quais dependem de cada cliente GPS, nem promete uma posição nova a cada minuto.
8. **Falhas seguras:** falha tipada Traccar resulta em HTTP 503, com JSON de erro sem coordenadas fabricadas. O navegador mantém eventual último mapa bem identificado como não atualizado. Endpoint JSON é `no-store`.
9. **Privacidade:** ambas as views exigem autenticação e `rastreamento.view_dispositivogps`, inclusive para a API JSON. Essa é uma mudança em relação ao legado (`frota.view_veiculo`), e requer atribuir a permissão GPS aos gestores autorizados. O token Traccar permanece apenas no servidor.
10. **MVP sem infraestrutura extra:** Leaflet/OpenStreetMap, Django e endpoints existentes; não introduzir Redis, Celery, WebSocket, job de coleta, microserviços nem relatórios históricos.
11. **Compatibilidade:** não remover o campo legado `Veiculo.traccar_device_id` nem alterar as operações de associação na Entrega 4, porque a Entrega 3 ainda o sincroniza e testa. A retirada definitiva será uma evolução isolada, com reconciliação de dados.

## Escopo excluído

- Mapa compacto no painel inicial (Entrega 5).
- Reprodução de trajetos, relatórios, rotas percorridas, geofencing, notificações e armazenamento duplicado.
- Alteração da taxa real de envio de coordenadas nos dispositivos.
- Alterações de schema ou migrações.

## Pendências e riscos

- Dados GPS podem ser imprecisos ou atrasar devido a rede, bateria, permissões do telefone ou falta de fix de satélite; o estado de conexão pode divergir do estado da posição.
- O serviço de tiles `tile.openstreetmap.org` depende de política de uso e disponibilidade de terceiros; em cenários de maior tráfego, avaliar provedor permitido e com atribuição correta.
- Não compartilhar `.env`, dumps de dados nem o ZIP contendo credenciais. Não publicar endpoints de rastreamento externamente antes de configurar HTTPS, autenticação e uma política de acesso/retenção.
- Cadastro público de usuários e permissões amplas dos CRUDs anteriores merecem revisão separada antes de uso operacional com terceiros.

## Rollback

A Entrega 4 não altera o banco: reverter o commit do patch restaura views/templates/URLs antigos. Persistem os vínculos existentes. Não usar `docker compose down -v`.
