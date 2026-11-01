from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("frota", "0002_veiculo_traccar_device_id_alter_motorista_cnh_numero"),
    ]

    operations = [
        migrations.CreateModel(
            name="DispositivoGPS",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120, verbose_name="nome administrativo")),
                ("traccar_id", models.PositiveBigIntegerField(unique=True, verbose_name="ID do dispositivo no Traccar")),
                ("unique_id", models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name="identificador único no Traccar")),
                ("ativo", models.BooleanField(default=True, verbose_name="ativo administrativamente")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("atualizado_em", models.DateTimeField(auto_now=True, verbose_name="atualizado em")),
                ("veiculo", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dispositivo_gps", to="frota.veiculo", verbose_name="veículo associado")),
            ],
            options={"verbose_name": "dispositivo GPS", "verbose_name_plural": "dispositivos GPS", "ordering": ("nome", "id")},
        ),
    ]
