## Executar localmente

**Pré-requisitos:** Docker com Compose 

```bash
git clone https://github.com/SEU-USUARIO/gestao-de-frotas-mvp.git
cd gestao-de-frotas-mvp
cp .env.example .env
```

 **Subindo com Docker e Criar SuperUsuário**
 
```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

| Acesso    | Endereço                               |
| --------- | -------------------------------------- |
| Sistema   | http://localhost:8000/auth/login/      |
| Dashboard | http://localhost:8000/auth/plataforma/ |
| Traccar   | http://localhost:8082/                 |


### GPS

1. Entre no **Traccar**, crie uma conta e cadastre um dispositivo de teste.
2. Gere um **token de API** no Traccar e informe `TRACCAR_API_TOKEN` no `.env`.
3. Recrie o serviço web: `docker compose up -d --force-recreate web`.
4. No Django, abra **Dispositivos GPS**, sincronize e associe o dispositivo a um veículo; depois abra **Mapa da Frota**.

