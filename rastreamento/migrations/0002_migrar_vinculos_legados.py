from django.db import migrations


def migrar_vinculos_legados(apps, schema_editor):
    """Preserva a associação GPS que hoje está no cadastro de veículos.

    Não se conecta ao Traccar: unique_id será preenchido posteriormente
    por uma sincronização autenticada e validada.
    """
    Veiculo = apps.get_model("frota", "Veiculo")
    DispositivoGPS = apps.get_model("rastreamento", "DispositivoGPS")
    banco = schema_editor.connection.alias

    vinculados = (
        Veiculo.objects.using(banco)
        .exclude(traccar_device_id__isnull=True)
        .values_list("id", "traccar_device_id")
        .iterator()
    )

    for veiculo_id, traccar_id in vinculados:
        dispositivo, criado = DispositivoGPS.objects.using(banco).get_or_create(
            traccar_id=traccar_id,
            defaults={
                "nome": f"GPS Traccar #{traccar_id} (migrado)",
                "veiculo_id": veiculo_id,
                "unique_id": None,
                "ativo": True,
            },
        )
        if not criado and dispositivo.veiculo_id != veiculo_id:
            raise RuntimeError(
                f"Conflito de associação para o Traccar #{traccar_id}: "
                f"GPS aponta para veículo {dispositivo.veiculo_id}, "
                f"mas o registro antigo aponta para {veiculo_id}. "
                "Interrompa e reconcilie os dados antes de prosseguir."
            )


class Migration(migrations.Migration):
    dependencies = [
        ("rastreamento", "0001_initial"),
        ("frota", "0002_veiculo_traccar_device_id_alter_motorista_cnh_numero"),
    ]

    operations = [
        migrations.RunPython(
            migrar_vinculos_legados,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
