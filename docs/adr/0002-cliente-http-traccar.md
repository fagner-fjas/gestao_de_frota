# ADR-0002 — Cliente HTTP isolado para o Traccar

- **Status:** Aceita para o MVP.
- **Data:** 2026-10-31.
- **Base:** `gestao_de_frota_atual_traccar.zip`.

## Contexto

A Entrega 1 criou `rastreamento.DispositivoGPS`, mas o cliente HTTP ainda ficava em `frota/services/traccar.py`. A página existente em `frota/views_rastreamento.py` depende de `listar_dispositivos`, `ultimas_posicoes` e `TraccarError`.

## Decisão

- Colocar o cliente HTTP em `rastreamento/services/client.py` e as operações de leitura nos serviços `dispositivos.py` e `localizacao.py`.
- Manter `frota/services/traccar.py` como **adaptador compatível**, sem novas regras de negócio, até a tela do mapa migrar de app.
- Usar token Bearer apenas no servidor; nunca enviá-lo ao navegador, nem registrar sua representação nos logs.
- Timeouts de conexão (3,05 s) e leitura (7 s), sem espera indefinida nem repetição automática neste MVP.
- Tratar configuração, autenticação, indisponibilidade e payload inválido com subclasses de `TraccarError`.
- Validar formato mínimo de dispositivos e últimas posições antes que a view processe os dados.
- Não persistir posições GPS no MySQL administrativo nem modificar migrações existentes.

## Motivações

A separação permite testar API sem MySQL/Traccar, reutilizar serviços em telas futuras e manter o MVP compreensível. O endpoint HTTP atual continua compatível.

## Alternativas postergadas

- Cache compartilhado e circuit breaker: implementar quando métricas justificarem.
- WebSocket: avaliar quando crescer o número de veículos; polling 60 s permanece planejado.
- Sincronização e cadastro de dispositivos via API: Entrega 3.
- Troca do campo legado `Veiculo.traccar_device_id`: fazer após migração de leitura, testes e reconciliação dos vínculos, em outra entrega.

## Riscos conhecidos

- O mapa atual ainda consulta duas rotas HTTP por atualização. Em indisponibilidade, o endpoint responde 503 sem revelar credenciais; verificações específicas de latência e limite de tráfego dependem do uso real.
- A conexão com Traccar por HTTP ocorre na rede interna do Docker. Em ambiente externo, exigir conexão protegida.
- Autorizações específicas de usuários e proteção do cadastro público devem ser tratadas antes de uso com rastreamento real de terceiros.
