

```bash
git clone https://github.com/fagner-fjas/gestao_de_frota.git
cd gestao_de_frota
```



```bash
cp .env.example .env
```

substitua DJANGO_SECRET_KEY por uma senha de 50 digitos

```bash
docker compose up -d --build
```


### Criar administrador Django

```bash
docker compose exec web python manage.py createsuperuser
```


- **Aplicação:** <http://localhost:8000/auth/login/>
- **Painel:** <http://localhost:8000/auth/plataforma/>
- **Admin Django:** <http://localhost:8000/admin/>
- **Traccar:** <http://localhost:8082/>





