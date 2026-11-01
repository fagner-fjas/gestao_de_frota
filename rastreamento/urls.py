from django.urls import path

from . import views, views_mapa

urlpatterns = [
    path('rastreamento/', views_mapa.mapa_frota, name='rastreamento'),
    path('rastreamento/dados/', views_mapa.dados_rastreamento, name='rastreamento_dados'),
    path('gps/', views.lista_dispositivos, name='gps_dispositivos'),
    path('gps/importar/', views.importar_dispositivos, name='gps_importar'),
    path('gps/<int:pk>/associar/', views.editar_associacao, name='gps_associar'),
]
