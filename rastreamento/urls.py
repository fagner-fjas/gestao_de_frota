from django.urls import path

from . import views

urlpatterns = [
    path('gps/', views.lista_dispositivos, name='gps_dispositivos'),
    path('gps/importar/', views.importar_dispositivos, name='gps_importar'),
    path('gps/<int:pk>/associar/', views.editar_associacao, name='gps_associar'),
]
