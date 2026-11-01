from django.db import models


class DispositivoGPS(models.Model):
    """Cadastro administrativo e associação 1:1 com a frota.

    O Traccar é a fonte de verdade para dispositivos e telemetria.
    O Django mantém apenas o vínculo e metadados administrativos.
    """

    nome = models.CharField("nome administrativo", max_length=120)
    traccar_id = models.PositiveBigIntegerField(
        "ID do dispositivo no Traccar", unique=True
    )
    # Nulo até a sincronização com a API (inclusive para vínculos legados).
    unique_id = models.CharField(
        "identificador único no Traccar",
        max_length=128,
        unique=True,
        null=True,
        blank=True,
    )
    veiculo = models.OneToOneField(
        "frota.Veiculo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispositivo_gps",
        verbose_name="veículo associado",
    )
    ativo = models.BooleanField("ativo administrativamente", default=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ("nome", "id")
        verbose_name = "dispositivo GPS"
        verbose_name_plural = "dispositivos GPS"

    def __str__(self):
        return f"{self.nome} (Traccar #{self.traccar_id})"
