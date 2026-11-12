# Migração incremental para o ZIP fornecido (após frota.0002).
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('frota', '0002_veiculo_traccar_device_id_alter_motorista_cnh_numero'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramacaoRecorrente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120)),
                ('dias_semana', models.CharField(max_length=13)),
                ('hora_partida', models.TimeField()),
                ('data_inicio', models.DateField()),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('ativa', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('motorista_padrao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='programacoes_padrao', to='frota.motorista')),
                ('veiculo_padrao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='programacoes_padrao', to='frota.veiculo')),
                ('rota', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='frota.rota')),
                ('passageiros', models.ManyToManyField(blank=True, to='frota.passageiro')),
            ],
            options={
                'ordering': ['nome', 'id'],
                'verbose_name': 'programação recorrente',
                'verbose_name_plural': 'programações recorrentes',
            },
        ),
        migrations.AddField(
            model_name='viagem', name='programacao_recorrente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='viagens', to='frota.programacaorecorrente'),
        ),
        migrations.AddField(
            model_name='viagem', name='data_programada',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='viagem', name='passageiros_embarcados',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='viagem', name='confirmado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='viagem', name='confirmado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='viagens_confirmadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='viagem',
            constraint=models.UniqueConstraint(fields=('programacao_recorrente', 'data_programada'), name='unica_viagem_por_programacao_data'),
        ),
    ]
