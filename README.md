# Gestão de Frotas — MVP

MVP de gerenciamento de veículos, motoristas, passageiros, rotas e viagens, desenvolvido com **Python / Django 5.2+, MySQL 8.4 e Docker Compose**. A aplicação utiliza um layout administrativo **TailAdmin / Tailwind CSS** e integra o **Traccar 6.16** para administração de dispositivos GPS e visualização da última posição conhecida dos veículos.

> **Finalidade:** ambiente de desenvolvimento, demonstração e testes do MVP. O `runserver` do Django, `DEBUG=1` e o servidor de arquivos estáticos atual **não configuram uma implantação de produção**.

## Funcionalidades

- CRUD e relacionamentos de **veículos, motoristas, passageiros, rotas e viagens**.
- Autenticação Django, painel operacional, indicadores, próximas viagens e atalhos.
- **Dispositivos GPS:** sincronização dos dispositivos cadastrados no Traccar e associação a veículos do Django.
- **Mapa da Frota:** exibe última posição, horário, velocidade e bateria quando enviados pelo rastreador. Distingue *posição recente*, *atrasada*, *desatualizada* e *sem posição*. A interface consulta os dados a cada **60 segundos**.
- **Mini mapa no painel inicial**, na última seção, disponível para usuários autorizados.
- **Testes automatizados** e decisões arquiteturais em [`docs/`](docs/).

A posição dos veículos **não é salva como histórico no MySQL do Django**: a API Traccar fornece a telemetria e o banco Django mantém os cadastros e vínculos administrativos.

## 1. Pré-requisitos

No computador que executará o projeto:

- **Docker Engine ou Docker Desktop**, com **Docker Compose v2** (`docker compose`).
- Git (para clonar; dispensável se recebeu o código em ZIP).
- Internet na primeira execução (download de imagens Docker, dependências e Tailwind CLI; o mapa usa tiles externos).
- Portas livres **8000** (Django), **8082** (Traccar web) e **5055/TCP** (recepção do protocolo de exemplo), ou escolha outras portas de host no `.env`.

Não é necessário instalar Python, MySQL, Node.js ou Tailwind globalmente no PC: as ferramentas rodam nos contêineres. **Docker no Linux pode exigir `sudo`** se o usuário não tiver acesso ao daemon.

Verificação:

```bash
docker --version
docker compose version
```

## 2. Obter o código e configurar o ambiente

```bash
git clone https://github.com/fagner-fjas/gestao_de_frota.git
cd gestao_de_frota
```

> Se a integração ainda estiver numa branch de Pull Request, faça checkout dessa branch antes da instalação. Em um ZIP, descompacte e entre na pasta que contém `docker-compose.yml`.

Crie suas configurações locais a partir do arquivo de exemplo:

```bash
cp .env.example .env
```

Edite `.env` e **substitua todas as senhas e a `DJANGO_SECRET_KEY`**. Você pode gerar uma chave com Python *no host* (quando houver Python disponível) ou usar qualquer gerador seguro de senhas; também pode gerar dentro do contêiner após construir as imagens. Exemplo com Python:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Use valores exclusivos para cada senha. Evite caracteres especiais não escapados como `$` no `.env`, pois o Compose pode interpolá-los. **Não publique o `.env` nem cole o seu conteúdo em issues, PRs ou relatórios.**

### Variáveis principais

| Variável | Finalidade | Exemplo de desenvolvimento |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Assinatura de sessões e segurança Django | Valor aleatório e exclusivo |
| `DJANGO_DEBUG` | Debug local | `1` |
| `DJANGO_ALLOWED_HOSTS` | Hosts HTTP permitidos | `localhost,127.0.0.1` |
| `DB_NAME`, `DB_USER` | Banco/usuário MySQL | `frota_mvp`, `frota_user` |
| `DB_PASSWORD`, `DB_ROOT_PASSWORD` | Senhas MySQL | Valores exclusivos |
| `DB_HOST`, `DB_PORT` | Endereço do banco **dentro do Docker** | `db`, `3306` |
| `TRACCAR_URL` | Endereço da API **a partir do Django** | `http://traccar:8082` |
| `TRACCAR_API_TOKEN` | Token Bearer do Traccar | Preenchido após criar no Traccar |
| `WEB_BIND_IP`, `WEB_PORT` | IP e porta expostos no PC para Django | `127.0.0.1`, `8000` |
| `TRACCAR_WEB_PORT` | Porta web do Traccar no PC | `8082` |
| `TRACCAR_DEVICE_BIND_IP`, `TRACCAR_DEVICE_PORT` | Interface/IP local do PC e porta de GPS | `127.0.0.1`, `5055` |

**Regra importante de rede:** dentro do contêiner web, `localhost` é o próprio contêiner. Por isso `DB_HOST=db` e `TRACCAR_URL=http://traccar:8082` devem permanecer assim no cenário padrão com Docker Compose.

## 3. Inicializar com Docker

```bash
docker compose config -q
docker compose up -d --build
docker compose ps
```

O serviço `web` aguarda a inicialização saudável do MySQL e executa as migrações ao iniciar. O serviço `tailwind` compila/observa os estilos CSS. Na primeira execução, consulte os logs se necessário:

```bash
docker compose logs --tail=80 web db traccar tailwind
```

Caso a folha de estilos não seja gerada automaticamente, execute uma compilação manual:

```bash
docker compose run --rm tailwind python manage.py tailwind --skip-checks build
```

### Criar administrador Django

```bash
docker compose exec web python manage.py createsuperuser
```

Depois, no **mesmo computador**:

- **Aplicação:** <http://localhost:8000/auth/login/>
- **Painel:** <http://localhost:8000/auth/plataforma/>
- **Admin Django:** <http://localhost:8000/admin/>
- **Traccar:** <http://localhost:8082/>

As portas acima se referem aos valores padrão do `.env.example`. Se você alterar `WEB_PORT` ou `TRACCAR_WEB_PORT`, ajuste as URLs.

## 4. Ativar o GPS (opcional para os CRUDs)

**O painel e os cadastros funcionam sem token do Traccar; a importação de GPS e a consulta de posições exigem a integração configurada.**

1. Abra a interface do **Traccar** em <http://localhost:8082/> e crie/configure sua conta administrativa conforme a interface da versão instalada.
2. Cadastre um dispositivo de teste no Traccar informando seu identificador único (*Unique ID*). Não confunda o ID interno numérico do Traccar com o identificador enviado pelo equipamento.
3. Gere um **token de API** na sua conta Traccar e coloque-o em `TRACCAR_API_TOKEN` no `.env`.
4. Reinicie o contêiner web para carregar o novo token:

   ```bash
   docker compose up -d --force-recreate web
   ```

5. Entre no Django com um usuário autorizado, abra **Dispositivos GPS** em `/gps/`, importe os dispositivos e **associe um dispositivo ao veículo** já cadastrado.
6. Confira **Mapa da Frota** em `/rastreamento/` ou o resumo GPS no painel principal.

O serviço `rastreamento` usa as permissões Django (`view_dispositivogps`, `add_dispositivogps`, `change_dispositivogps`). O superusuário possui essas permissões por padrão; configure as permissões dos demais usuários no admin.

### Usar um celular ou equipamento na mesma rede (Wi-Fi/LAN)

**Por segurança**, o Compose expõe a porta do GPS somente em `127.0.0.1` por padrão. Assim, **um celular não conseguirá enviar dados pela rede até configurar o endereço do host**:

1. Descubra o **IP IPv4 LAN do computador** que executa o Docker (não o endereço do contêiner).
2. No `.env`, configure `TRACCAR_DEVICE_BIND_IP` para esse IP. Exemplo fictício: `192.168.1.50`.
3. Recrie o serviço Traccar para aplicar a nova publicação da porta:

   ```bash
   docker compose up -d --force-recreate traccar
   ```

4. No cliente GPS de teste, escolha o **protocolo compatível** e configure o IP do PC e a porta `5055` (padrão deste protótipo para OsmAnd). Verifique firewall e isolamento entre os dispositivos da rede.

Se mudar `TRACCAR_DEVICE_PORT`, use essa nova porta no cliente. Outros modelos de rastreadores utilizam protocolos e portas diferentes, que não estão automaticamente liberados por este Compose. **Mantenha a porta restrita à sua rede autorizada; não exponha a administração do Traccar nem o Django diretamente à internet.**

### Acessar a aplicação de outro computador da rede

A instalação padrão só aceita conexões locais. Para permitir acesso **apenas na LAN de confiança**, configure no `.env`:

```dotenv
WEB_BIND_IP=192.168.1.50
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
```

Use o IP **real do computador host**; esses números são ilustrativos. Recrie o serviço e acesse `http://IP_DO_PC:8000/auth/login/` a partir do outro computador:

```bash
docker compose up -d --force-recreate web
```

Libere acesso somente a dispositivos autorizados no firewall. Como o projeto usa Django `runserver` e `DEBUG=1`, **esta configuração é exclusiva para demonstração numa LAN controlada**, não para publicar o site na internet.

## 5. Testes automatizados

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test frota usuarios rastreamento -v 2
```

> **MySQL:** em uma instalação nova, o usuário `DB_USER` criado pela imagem oficial pode não ter direito de criar o banco temporário `test_<DB_NAME>`. Se a suíte falhar com *Access denied* ao criar o banco de testes, conceda ao usuário permissões **somente no banco de testes** com uma conta administrativa. Por exemplo, usando os valores de demonstração de `.env.example`, entre com `docker compose exec db mysql -u root -p` e execute `GRANT ALL PRIVILEGES ON test_frota_mvp.* TO 'frota_user'@'%';`. Para outras configurações, adapte o nome do banco e do usuário. Isso se aplica a **ambiente de desenvolvimento**, não ao banco de produção.

## 6. Operação e manutenção

```bash
# Inspecionar serviços
docker compose ps

# Logs dos serviços
docker compose logs -f --tail=100 web traccar

# Atualizar código após git pull (migrações rodam no início do web)
docker compose up -d --build

# Desligar sem excluir bancos
docker compose down
```

**Persistência:** o MySQL usa o volume `mysql_data`. O Traccar usa `traccar_data` e `traccar_logs`. Esses volumes sobrevivem a `docker compose down` e `up` normais, mas **`docker compose down -v` os exclui**: não execute esse comando se houver dados que deseja preservar.

Para receber uma instalação nova sem os dados anteriores, o administrador deve cadastrar novamente usuários, veículos e dispositivos, pois não foram distribuídos backups do banco.

## 7. Estrutura do projeto

```text
gestao_de_frota/
├── frota/               # Modelos, CRUDs e viagens
├── usuarios/            # Autenticação e dashboard
├── rastreamento/        # GPS, Traccar, vínculos e mapa
│   ├── services/        # Cliente HTTP, sincronização e monitoramento
│   └── migrations/      # Modelo GPS e migração de vínculos antigos
├── templates/           # Layout principal e sidebar TailAdmin
├── assets/              # CSS/JavaScript e recursos estáticos
├── tailwind/             # Fonte dos estilos Tailwind
├── docs/                 # ADRs e histórico das entregas
├── projeto_mvp/          # Configuração Django
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Limitações e segurança

- O MVP exibe **últimas posições conhecidas**, não rota histórica, geofencing ou alertas automáticos.
- Os limites de tempo de posição foram definidos para o protótipo, não equivalem à disponibilidade de rede real do equipamento.
- O token da API Traccar fica **somente no backend**. Não inclua senhas, tokens ou dados de localização reais em commits, prints públicos ou chamados.
- O front-end depende de recursos externos (Leaflet/OpenStreetMap e Alpine via CDN) para renderizar todos os recursos.
- A publicação em produção exige revisão de segurança, HTTPS, servidor WSGI/ASGI adequado, configuração de estáticos, backups e configuração de contas/permissões.

**Documentação técnica complementar:** [`docs/etapas/`](docs/etapas/) e [`docs/adr/`](docs/adr/).
