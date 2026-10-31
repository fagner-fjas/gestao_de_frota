# Entrega 2 — Cliente Traccar com testes e compatibilidade

## Escopo

Esta entrega **não** altera modelos/migrações, nem as URLs ou templates do mapa. Tem foco no isolamento da integração HTTP do Traccar. O projeto continua sendo um MVP.

## Arquivos

- `rastreamento/services/client.py`: configurações, autenticação, HTTP e erros tipados.
- `rastreamento/services/dispositivos.py`: lista de dispositivos (`/api/devices`).
- `rastreamento/services/localizacao.py`: últimas posições (`/api/positions`).
- `frota/services/traccar.py`: adaptador que preserva imports legados.
- `rastreamento/tests_api.py`: testes de serviço com mocks, sem servidor real.
- `docs/adr/0002-cliente-http-traccar.md`: decisão arquitetural.

## Validação no Linux Mint, na raiz do projeto

Antes de começar, confira a branch e preserve mudanças não commitadas:

```bash
git status
sudo docker compose config --quiet
sudo docker compose exec web python manage.py check
sudo docker compose exec web python manage.py showmigrations frota rastreamento
```

Aplicar o patch (após copiá-lo para Downloads):

```bash
git apply --check ~/Downloads/entrega_02_traccar_api.patch
git apply ~/Downloads/entrega_02_traccar_api.patch
```

A aplicação do patch altera arquivos imediatamente por causa de `.:/app`; não é necessário reiniciar contêiner só para Python recarregar no `runserver`.

Testes:

```bash
sudo docker compose exec web python manage.py check
sudo docker compose exec web python manage.py makemigrations --check --dry-run
sudo docker compose exec web python manage.py test rastreamento.tests_api -v 2
sudo docker compose exec web python manage.py test frota usuarios rastreamento -v 2
```

**Atenção:** se a classe antiga `RotaCrudTest.test_validacoes` falhar, investigar separadamente, sem associar isso à integração GPS. O ZIP atual mostra a correção de indentação desse método.

Acesso visual para teste manual com um usuário autenticado e com permissão `frota.view_veiculo`:

- `http://localhost:8000/rastreamento/`
- `http://localhost:8000/rastreamento/dados/`

Com o dispositivo transmitindo ao Traccar, deve aparecer a localização no mapa. Não divulgar coordenadas reais nem credenciais ao compartilhar logs.

## Critérios de aceite

1. A suíte HTTP isolada passa sem conexão à internet nem servidor Traccar ativo.
2. Endpoints existentes `rastreamento/` e `rastreamento/dados/` continuam respondendo.
3. O token Traccar permanece no backend, e erros de conexão não o expõem.
4. Falhas 401/403, timeout, indisponibilidade e JSON inválido são tratadas com erros específicos.
5. `python manage.py makemigrations --check --dry-run` não identifica migrações pendentes introduzidas por esta entrega.
6. O campo legado permanece intocado até a troca planejada da leitura de vínculos.

## Rollback do código

Faça commit antes de aplicar. Se a integração apresentar regressão, restaure pelo Git **somente os arquivos deste patch**, ou reverta o commit correspondente. Não rode `docker compose down -v` nem remova migrações.
