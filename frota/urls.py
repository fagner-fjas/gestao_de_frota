from django.urls import path

from . import views

urlpatterns = [
    # Rotas
    path('rotas/', views.RotaLista.as_view(), name='rota_lista'),
    path('rotas/nova/', views.RotaCriar.as_view(), name='rota_nova'),
    path('rotas/<int:pk>/', views.RotaDetalhe.as_view(), name='rota_detalhe'),
    path('rotas/<int:pk>/editar/', views.RotaEditar.as_view(), name='rota_editar'),
    path('rotas/<int:pk>/excluir/', views.RotaExcluir.as_view(), name='rota_excluir'),

    # Motoristas
    path('motoristas/', views.MotoristaLista.as_view(), name='motorista_lista'),
    path('motoristas/novo/', views.MotoristaCriar.as_view(), name='motorista_nova'),
    path('motoristas/<int:pk>/', views.MotoristaDetalhe.as_view(), name='motorista_detalhe'),
    path('motoristas/<int:pk>/editar/', views.MotoristaEditar.as_view(), name='motorista_editar'),
    path('motoristas/<int:pk>/excluir/', views.MotoristaExcluir.as_view(), name='motorista_excluir'),

    # Veículos
    path('veiculos/', views.VeiculoLista.as_view(), name='veiculo_lista'),
    path('veiculos/novo/', views.VeiculoCriar.as_view(), name='veiculo_nova'),
    path('veiculos/<int:pk>/', views.VeiculoDetalhe.as_view(), name='veiculo_detalhe'),
    path('veiculos/<int:pk>/editar/', views.VeiculoEditar.as_view(), name='veiculo_editar'),
    path('veiculos/<int:pk>/excluir/', views.VeiculoExcluir.as_view(), name='veiculo_excluir'),

    # Passageiros
    path('passageiros/', views.PassageiroLista.as_view(), name='passageiro_lista'),
    path('passageiros/novo/', views.PassageiroCriar.as_view(), name='passageiro_nova'),
    path('passageiros/<int:pk>/', views.PassageiroDetalhe.as_view(), name='passageiro_detalhe'),
    path('passageiros/<int:pk>/editar/', views.PassageiroEditar.as_view(), name='passageiro_editar'),
    path('passageiros/<int:pk>/excluir/', views.PassageiroExcluir.as_view(), name='passageiro_excluir'),

    # Viagens
    path('viagens/', views.ViagemLista.as_view(), name='viagem_lista'),
    path('viagens/nova/', views.ViagemCriar.as_view(), name='viagem_nova'),
    path('viagens/<int:pk>/', views.ViagemDetalhe.as_view(), name='viagem_detalhe'),
    path('viagens/<int:pk>/editar/', views.ViagemEditar.as_view(), name='viagem_editar'),
    path('viagens/<int:pk>/excluir/', views.ViagemExcluir.as_view(), name='viagem_excluir'),
    path('viagens/<int:pk>/<str:acao>/', views.mudar_status, name='viagem_status'),
]
