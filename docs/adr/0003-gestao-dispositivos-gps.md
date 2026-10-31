# ADR-0003 — Gestão de dispositivos GPS e vínculo com veículos

- **Status:** proposta implementada, pendente validação no Docker do usuário
- **Data:** 2026-10-31
- **Origem:** `gestao_de_frota_passo2.zip` (Entregas 1 e 2)

## Contexto

O modelo `rastreamento.DispositivoGPS` já existe e mantém vínculos administrativos.
A página de mapa existente (`frota/views_rastreamento.py`) ainda lê `frota.Veiculo.traccar_device_id`.
A API HTTP modular já oferece `listar_dispositivos()` sem persistência.
O MVP necessita de importação e associação, mas não de criação remota nem de relatórios.

## Decisões

1. **Fonte de verdade:** IDs e `uniqueId` vêm do Traccar; o Django armazena os metadados administrativos e o vínculo com a frota.
2. **Importação unidirecional:** botão POST protegido por CSRF e permissão `rastreamento.add_dispositivogps`, consumindo `GET /api/devices`. Não criamos, editamos nem removemos dispositivos remotamente.
3. **Importação idempotente e atômica:** valida a lista inteira antes de gravar; repetições não duplicam registros; nomes locais personalizados, vínculos e status `ativo` não são sobrescritos. Divergências de identidade interrompem a importação.
4. **Vínculo:** um GPS para no máximo um veículo e vice-versa. O formulário só oferece veículos sem vínculo no modelo novo. O serviço também recusa conflito com o campo legado, inclusive quando o formulário é burlado.
5. **Compatibilidade transitória:** a associação atualiza `DispositivoGPS.veiculo` e `Veiculo.traccar_device_id` na mesma transação, até que a Entrega 4 altere a leitura do mapa.
6. **Permissões:** usuários com `view_dispositivogps` consultam; `add_dispositivogps` importa; `change_dispositivogps` associa. `DispositivoGPSAdmin` permanece somente leitura; exclusão não é oferecida.
7. **Transferência:** primeiro desvincular, depois vincular outro veículo. Dispositivos administrativos inativos não podem criar novos vínculos.
8. **Status Traccar:** `ativo` é status administrativo, não significa online/offline. O mapa continua legado e é tratado na Entrega 4.
9. **Paginação:** 20 registros por página, sem chamadas automáticas ao Traccar na listagem.

## Escopo excluído

- Cadastro/alteração/exclusão de GPS por POST na API Traccar.
- Mapa global no dashboard; sincronização agendada; histórico e relatórios.
- Remoção do campo legado e migrações estruturais (não são necessárias na Entrega 3).

## Riscos/pendências

- Durante a transição, código legado externo ao módulo ainda pode editar `Veiculo.traccar_device_id` por shell ou admin. A associação rejeita conflitos, mas não consegue impedir edições manuais posteriores. A Entrega 4 elimina o campo redundante, após reconciliação.
- Dispositivos inexistentes no snapshot remoto não são excluídos automaticamente. A decisão evita perda de vínculos por falhas, permissões do token ou filtro da API.
- A rota pública de criação de conta (`/auth/cadastro/`) e os CRUDs legados têm controles de autorização limitados. Antes de monitorar veículos de terceiros em produção, restringir o cadastro e revisar as permissões de todo o sistema.
- A importação pressupõe `uniqueId` válido em `/api/devices`. Equipamentos sem identificador válido exigem correção no Traccar; a importação não inventa IDs.

## Validação

- Executar `manage.py check`, `makemigrations --check --dry-run`, testes do app e suíte completa no Docker.
- Simular importação com API indisponível, payload inválido e divergência de identidade, verificando que não há gravações parciais.
- Verificar vínculo/desvínculo nas duas tabelas e consultar `/rastreamento/dados/` antes e depois.
