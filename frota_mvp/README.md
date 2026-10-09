
## Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt
```

## Configurar o MySQL

1. Abra o cliente do MySQL (`mys sql -u root -p`) e crie o banco (uma única vez):

   ```sql
   CREATE DATABASE frota_mvp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. Informe ao Django a senha do seu MySQL. Duas opções:

   - Editar o valor padrão de `PASSWORD` em `projeto_mvp/settings.py`; **ou**
   - Definir variáveis de ambiente (não vão para o Git):

     ```bash
     export DB_PASSWORD="sua_senha"      
     ```

   Também existem `DB_USER`, `DB_NAME`, `DB_HOST` e `DB_PORT` (padrões:
   `root`, `frota_mvp`, `127.0.0.1`, `3306`).

## Criar as tabelas (migrations)

```bash
python manage.py makemigrations
python manage.py migrate
```

## Criar um usuário

Pelo próprio sistema (recomendado): acesse `/auth/cadastro/`.

Para o painel administrativo (`/admin/`), crie um superusuário:

```bash
python manage.py createsuperuser
```

## Executar

```bash
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

## Telas

| Tela                | Endereço             |

| Cadastro de usuário | `/auth/cadastro/`    |


| Login               | `/auth/login/`       |


| Plataforma          | `/auth/plataforma/`  |


| Rotas               | `/rotas/`            |

| Motoristas          | `/motoristas/`       |

| Veículos            | `/veiculos/`         |

| Passageiros         | `/passageiros/`      |


| Viagens             | `/viagens/`          |


## Como testar os CRUDs

1. Cadastre-se em `/auth/cadastro/` e faça login
2. Crie 1 rota, 1 motorista, 1 veículo e 1 passageiro
3. Em cada lista: confira o registro, busque, abra (Ver), edite e exclua
4. Em `/viagens/nova/`, agende uma viagem com data futura
5. Na tela da viagem, use Iniciar / Concluir / Cancelar
6. Tente excluir uma rota que já tem viagem: o sistema bloqueia
7. Confira no MySQL: `SELECT * FROM frota_rota;`


