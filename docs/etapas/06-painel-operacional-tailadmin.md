# Entrega 6 — Painel operacional alinhado ao TailAdmin

## Objetivo
Reorganizar o dashboard inicial para priorizar os indicadores e as tarefas administrativas. O mapa de rastreamento GPS passa a ser a **última seção** do painel, sem duplicar o endpoint nem as regras de negócio do app `rastreamento`.

## Alterações
- Cabeçalho com data e atalho **Nova viagem**.
- Quatro indicadores com ícones e hierarquia visual consistente com as classes do TailAdmin/Tailwind v4 já usadas no projeto.
- Próximas viagens em tabela responsiva.
- Nova coluna **Situação operacional** com contagem de viagens em andamento, manutenção e CNHs que exigem atenção.
- Acessos rápidos para cadastrar veículo, rota ou motorista.
- Mapa e cards GPS reposicionados para **depois de todos os blocos administrativos**.
- Widget GPS mantido somente para usuários com `rastreamento.view_dispositivogps`.
- Mini mapa renderiza todas as posições, enquanto a lista lateral resume os cinco primeiros veículos; informa quando há mais.
- Geração do conteúdo de nomes e status no mini mapa via `textContent`, sem HTML não confiável.
- Atribuição do OpenStreetMap exibida no mapa (Leaflet).
- Sem mudanças em modelos, migrações, API, Docker ou dados persistidos.

## Hierarquia visual
1. Saudação, data e atalho Nova viagem.
2. Indicadores de viagens, veículos e motoristas.
3. Próximas viagens + situação operacional / acessos rápidos.
4. Rastreamento GPS (última seção para usuários autorizados).

## Fonte de dados
- Métricas administrativas: contexto já calculado em `usuarios.views.plataforma`.
- Métricas GPS: `/rastreamento/dados/`, permissão `rastreamento.view_dispositivogps`, consultas a cada 60 segundos.

## Testes
Atualizamos os testes de apresentação da Entrega 5 (nome do bloco GPS) e acrescentamos testes da ordem do dashboard, dos links de atalho e do painel sem autorização GPS.

## Referências
- TailAdmin — Layout: https://tailadmin.com/docs/app-layout
- TailAdmin — Customização: https://tailadmin.com/docs/customizations

## Fora do escopo
- Relatórios históricos e telemetria persistida no Django.
- Alterações no Traccar.
- Refatoração das regras de negócio de Viagem, Motorista ou Veiculo.
