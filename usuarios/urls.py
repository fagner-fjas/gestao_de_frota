from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('logout/', views.sair, name='logout'),
    path('plataforma/', views.plataforma, name='plataforma'),
]
