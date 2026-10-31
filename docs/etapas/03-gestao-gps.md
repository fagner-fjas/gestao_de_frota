# Entrega 3 — Dispositivos GPS no Django (MVP)

## Objetivo

Importar os dispositivos já cadastrados no Traccar e associá-los a veículos no sistema de frotas, com permissões, transações e testes. Sem implementação de relatório ou mapa novo.

## Mudanças

- `rastreamento/services/sincronizacao.py`: valida e importa snapshot remoto de maneira atômica e idempotente.
- `rastreamento/services/associacoes.py`: transação de associação/desvinculação com compatibilidade do campo legado.
- `rastreamento/forms.py`, `views.py`, `urls.py`: formulário e views autorizadas.
- `rastreamento/templates/rastreamento/*`: telas integradas ao `base.html` TailAdmin.
- `templates/partials/sidebar.html`: seção GPS visível somente para quem tem permissões.
- `frota/forms.py`: retira `traccar_device_id` do formulário genérico de veículo, mantendo o campo no modelo.
- `projeto_mvp/urls.py`: inclui as URLs do novo app.
- `rastreamento/tests_gestao.py`: cobertura da importação, vínculo, bloqueios e regressão do legado.
- `docs/adr/0003-gestao-dispositivos-gps.md`: decisão arquitetural.

## URLs

- `GET /gps/` — lista paginada de dispositivos importados (permissão `view_dispositivogps`).
- `POST /gps/importar/` — sincronização (permissão `add_dispositivogps` e CSRF).
- `GET/POST /gps/<id>/associar/` — associação e desvinculação (`change_dispositivogps` e CSRF no POST).
- `/rastreamento/` e `/rastreamento/dados/` — continuam legados, **sem mudanças nesta entrega**.

## Antes de aplicar

```bash
cd "$HOME/Área de trabalho/gestao_de_frota"
git status
sudo docker compose config --quiet
sudo docker compose exec web python manage.py showmigrations frota rastreamento
```

Preserve mudanças locais com commit/stash e crie uma branch `feature/gps-dispositivos`. Tenha backup válido do MySQL e do Traccar. O patch não possui migrações nem operações destrutivas.

## Aplicação

Salve `entrega_03_gerenciamento_gps.patch` na pasta Downloads e execute:

```bash
git apply --check "$HOME/Downloads/entrega_03_gerenciamento_gps.patch"
git apply "$HOME/Downloads/entrega_03_gerenciamento_gps.patch"
git diff --check
sudo docker compose exec web python manage.py check
sudo docker compose exec web python manage.py makemigrations --check --dry-run
sudo docker compose exec web python manage.py test rastreamento -v 2
sudo docker compose exec web python manage.py test frota usuarios rastreamento -v 2
```

**Não executar** `docker compose down -v`. O volume de código em `web` é `.:/app`; alterações passam ao contêiner de desenvolvimento.

## Permissões administrativas

Entre em `http://localhost:8000/admin/` com um superusuário. Para um gestor não-superusuário, configure em Usuários/Grupos as permissões:

- `rastreamento | dispositivo GPS | Can view dispositivo GPS`
- `rastreamento | dispositivo GPS | Can add dispositivo GPS` (sincronização)
- `rastreamento | dispositivo GPS | Can change dispositivo GPS` (vincular/desvincular)

Permissões de `view_veiculo` do app Frota continuam controlando o mapa legado. As permissões são criadas pelo Django quando as migrações do app são aplicadas. Não é necessário conceder `delete_dispositivogps`.

## Teste manual (usar dispositivo pessoal/autorizado)

1. Acesse `http://localhost:8000/gps/` como superusuário/gestor autorizado.
2. Clique em **Sincronizar com Traccar**; os dispositivos cadastrados no Traccar deverão aparecer.
3. Clique em **Associar**; escolha um veículo sem GPS e salve.
4. Volte à listagem; confirme veículo associado. Consulte `/rastreamento/` e `/rastreamento/dados/` para verificar o mapa antigo.
5. Selecione **Nenhum — GPS disponível**, salve e confirme que o campo legado foi limpo.
6. Faça nova importação: nenhuma duplicata ou vínculo apagado.
7. Repita com usuário sem permissão; acesso deve ser negado.

## Critérios de aceite

- Importações repetidas não criam duplicatas.
- Falha remota ou conflito de identidade não deixa importação parcialmente aplicada.
- O usuário comum sem autorização não consegue listar, importar ou associar.
- Vínculo 1:1 respeitado e sincronizado temporariamente com o campo legado.
- `python manage.py makemigrations --check --dry-run` não encontra alterações pendentes.
- Testes novos e antigos passam no Docker; mapa legado não sofre regressões.

## Rollback

Se necessário, reverta o commit desta entrega usando Git (recomendado). Se o patch foi aplicado sem commit, reveja `git diff` e reverta somente os arquivos da Entrega 3. Nenhuma migração estrutural é aplicada. Registros de GPS criados pela importação no MySQL persistem; não os apague automaticamente no rollback.
