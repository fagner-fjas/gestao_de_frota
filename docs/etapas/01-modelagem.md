# Entrega 1 — Modelagem e migração segura dos dispositivos GPS

## Base verificada

- Fonte: `gestao_de_frota_atual(1).zip`; app `frota` e migração `frota.0002` já definem `Veiculo.traccar_device_id`.
- `web` monta `.:/app` e executa `migrate` na inicialização.
- O projeto usa Docker Compose, Django/MySQL e Traccar em serviços independentes.
- Não se valida o funcionamento do banco ou do servidor apenas com o ZIP.

## Antes de aplicar o patch

1. Confirmar `git status`, branch, `docker compose config --quiet` e o estado de `frota.0002` (`python manage.py showmigrations frota`). Salvar ou commitar alterações não versionadas.
2. Criar branch dedicada: `git switch -c feature/rastreamento-modelagem` (se não existir).
3. Criar um backup MySQL fora do repositório, com controle de acesso. Exemplo (a partir da raiz):

```bash
mkdir -p ../backups-frota
chmod 700 ../backups-frota
sudo docker compose exec -T db sh -c 'exec mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > "../backups-frota/mysql-$(date +%Y%m%d-%H%M%S).sql"
```

4. Preservar também o volume `traccar_data` por um mecanismo de backup apropriado antes de mudanças de infraestrutura; esta entrega não altera dados do Traccar.

**Nunca** fazer `down -v`, alterar ou excluir migrações antigas para “limpar” erros.

## Aplicar a entrega

```bash
git apply --check ~/Downloads/entrega_01_rastreamento.patch
git apply ~/Downloads/entrega_01_rastreamento.patch
sudo docker compose exec web python manage.py check
sudo docker compose exec web python manage.py makemigrations --check --dry-run
sudo docker compose exec web python manage.py migrate --plan
```

Verificar o plano de migração antes da execução. **Atenção**: o serviço `web` executa `python manage.py migrate` na inicialização; aplicar o patch a um contêiner já em execução, com bind mount, não requer reiniciar. **Não recrie ou reinicie `web` antes do backup, pois isso pode disparar migrações automaticamente.**

Depois do backup e da conferência do plano:

```bash
sudo docker compose exec web python manage.py migrate rastreamento
sudo docker compose exec web python manage.py test rastreamento
```

Para conferir os vínculos (não mostra credenciais ou coordenadas):

```bash
sudo docker compose exec web python manage.py shell -c '
from frota.models import Veiculo
from rastreamento.models import DispositivoGPS
origem = Veiculo.objects.exclude(traccar_device_id__isnull=True)
destino = DispositivoGPS.objects.exclude(veiculo__isnull=True)
print("Veículos vinculados antigos:", origem.count())
print("Dispositivos vinculados novos:", destino.count())
print("Associações preservadas:", all(
    v.dispositivo_gps.traccar_id == v.traccar_device_id
    for v in origem.select_related("dispositivo_gps")
))
'
```

Se a contagem ou correspondência falhar, **não avance** para remover campo antigo ou alterar telas.

## Critérios de aceite

- `manage.py check` sem erros.
- `makemigrations --check --dry-run` não encontra mudanças não migradas.
- `frota.0002`, `rastreamento.0001` e `rastreamento.0002` aplicadas.
- IDs de dispositivos que estavam em `Veiculo` migraram para `DispositivoGPS` sem divergência.
- Testes de unicidade, associação opcional, exclusão e preservação de dispositivo passam.
- Tela atual `/rastreamento/` continua funcionando pelo campo legado (compatibilidade intencional).
- Nenhuma credencial incluída no patch.

## Reversão planejada

Durante esta entrega o código antigo **continua funcionando**. Caso precise desfazer o novo esquema, só depois de validar o backup e garantir que nenhuma associação nova tenha sido cadastrada, seria possível reverter as migrações do `rastreamento` e remover o patch. Em produção, prefira uma migração corretiva em vez de apagar migrações já distribuídas.
