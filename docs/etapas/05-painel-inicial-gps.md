# Entrega 5 — Resumo do rastreamento no painel inicial

## Objetivo
Adicionar ao painel principal um resumo operacional do monitoramento GPS, reutilizando o endpoint já existente `/rastreamento/dados/`, sem criar nova persistência de telemetria.

## Escopo
- Cards com total monitorado, posições recentes, posições antigas e veículos sem posição.
- Mini mapa no painel principal.
- Lista resumida de veículos monitorados.
- Atualização automática a cada 60 segundos.
- Links para a gestão de dispositivos e para o mapa completo.
- Ícones específicos na sidebar para `Dispositivos GPS` e `Mapa da Frota`.

## Fora de escopo
- Histórico de posições.
- Novas migrações.
- Alterações na API do Traccar.
