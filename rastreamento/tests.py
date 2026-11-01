from django.db import IntegrityError, transaction
from django.test import TestCase

from frota.models import Veiculo
from rastreamento.models import DispositivoGPS


class DispositivoGPSTests(TestCase):
    @staticmethod
    def novo_veiculo(placa):
        return Veiculo.objects.create(
            placa=placa,
            marca="Teste",
            modelo="Van",
            ano=2022,
            tipo=Veiculo.Tipo.VAN,
            capacidade=12,
        )

    def test_dispositivo_pode_ficar_sem_veiculo(self):
        gps = DispositivoGPS.objects.create(nome="GPS reserva", traccar_id=11)
        self.assertIsNone(gps.veiculo_id)
        self.assertIsNone(gps.unique_id)

    def test_associacao_com_veiculo(self):
        veiculo = self.novo_veiculo("TESTE001")
        gps = DispositivoGPS.objects.create(
            nome="GPS do teste", traccar_id=12, veiculo=veiculo
        )
        self.assertEqual(veiculo.dispositivo_gps.pk, gps.pk)

    def test_veiculo_nao_pode_ter_dois_gps(self):
        veiculo = self.novo_veiculo("TESTE002")
        DispositivoGPS.objects.create(nome="GPS A", traccar_id=13, veiculo=veiculo)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DispositivoGPS.objects.create(
                    nome="GPS B", traccar_id=14, veiculo=veiculo
                )

    def test_traccar_id_unico(self):
        DispositivoGPS.objects.create(nome="GPS A", traccar_id=15)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DispositivoGPS.objects.create(nome="GPS B", traccar_id=15)

    def test_exclusao_do_veiculo_preserva_dispositivo(self):
        veiculo = self.novo_veiculo("TESTE003")
        gps = DispositivoGPS.objects.create(
            nome="GPS existente", traccar_id=16, veiculo=veiculo
        )
        veiculo.delete()
        gps.refresh_from_db()
        self.assertIsNone(gps.veiculo_id)
