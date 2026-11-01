from django.contrib import admin

from .models import Motorista, Passageiro, Rota, Veiculo, Viagem

admin.site.register([Rota, Motorista, Veiculo, Passageiro, Viagem])
