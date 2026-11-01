from django.contrib import admin

from .models import DispositivoGPS


@admin.register(DispositivoGPS)
class DispositivoGPSAdmin(admin.ModelAdmin):
    """Consulta administrativa durante a etapa de modelagem.

    Alterações e importações de GPS serão feitas na etapa 3, com
    permissões dedicadas, sincronização e validação do Traccar.
    """

    list_display = ("nome", "traccar_id", "unique_id", "veiculo", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "unique_id", "veiculo__placa")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
