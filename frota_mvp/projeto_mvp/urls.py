from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),   # login, cadastro, logout, plataforma
    path('', include('frota.urls')),           # rotas, motoristas, veículos, passageiros, viagens
    path('', RedirectView.as_view(pattern_name='plataforma')),
]
