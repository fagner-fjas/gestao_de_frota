



---

## Rodar com Docker


### 1. Pré-requisitos

- [Docker](https://docs.docker.com/engine/install/) e Docker Compose v

Teste com:

```bash
docker --version
docker compose version
```

### 2. Clonar o projeto

```bash
git clone https://github.com/fagner-fjas/gestao_de_frota.git
cd gestao_de_frota
```

### 3. Criar o arquivo `.env`

Criar .env e compor por: 

Conteúdo esperado:

```
DJANGO_SECRET_KEY=troque-por-uma-chave
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

DB_NAME=frota_mvp
DB_USER=frota_user
DB_PASSWORD=troque-essa-senha
DB_ROOT_PASSWORD=troque-essa-senha-root
DB_HOST=db
DB_PORT=3306
```


### 4. Subir os containers

```bash
docker compose up --build
```



As migrações rodam automaticamente na subida


