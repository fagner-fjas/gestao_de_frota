"""Testes isolados da comunicação Traccar, sem servidor nem banco de dados."""

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from frota.services import traccar as legado
from rastreamento.services.client import (
    TIMEOUT,
    TraccarAuthError,
    TraccarConfigError,
    TraccarResponseError,
    TraccarUnavailableError,
    traccar_get,
)
from rastreamento.services.dispositivos import listar_dispositivos
from rastreamento.services.localizacao import ultimas_posicoes


@override_settings(TRACCAR_URL='http://traccar:8082', TRACCAR_API_TOKEN='token-ficticio')
class TraccarAPITests(SimpleTestCase):
    def resposta(self, conteudo, status=200):
        response = Mock(status_code=status)
        response.json.return_value = conteudo
        return response

    @patch('rastreamento.services.client.requests.get')
    def test_dispositivos_valido_e_autenticado(self, get):
        get.return_value = self.resposta([{'id': 7, 'name': 'GPS de teste'}])
        self.assertEqual(listar_dispositivos()[0]['id'], 7)
        args, kwargs = get.call_args
        self.assertEqual(args[0], 'http://traccar:8082/api/devices')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer token-ficticio')
        self.assertEqual(kwargs['timeout'], TIMEOUT)
        self.assertFalse(kwargs['allow_redirects'])

    @patch('rastreamento.services.client.requests.get')
    def test_ultima_posicao(self, get):
        dados = [{'deviceId': 7, 'latitude': -7.67, 'longitude': -36.88}]
        get.return_value = self.resposta(dados)
        self.assertEqual(ultimas_posicoes(), dados)
        self.assertEqual(get.call_args.args[0], 'http://traccar:8082/api/positions')

    @patch('rastreamento.services.client.requests.get')
    def test_interface_legada_permanece_funcionando(self, get):
        get.return_value = self.resposta([{'id': 8, 'name': 'Outro GPS'}])
        self.assertEqual(legado.listar_dispositivos()[0]['id'], 8)

    @override_settings(TRACCAR_API_TOKEN='')
    @patch('rastreamento.services.client.requests.get')
    def test_token_ausente_bloqueia_requisicao(self, get):
        with self.assertRaises(TraccarConfigError):
            listar_dispositivos()
        get.assert_not_called()

    @patch('rastreamento.services.client.requests.get')
    def test_sem_autorizacao(self, get):
        for status in (401, 403):
            get.return_value = self.resposta({}, status)
            with self.subTest(status=status), self.assertRaises(TraccarAuthError):
                listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_timeout(self, get):
        get.side_effect = requests.Timeout('token-ficticio NUNCA DEVE SER EXIBIDO')
        with self.assertRaises(TraccarUnavailableError) as erro:
            listar_dispositivos()
        self.assertNotIn('token-ficticio', str(erro.exception))

    @patch('rastreamento.services.client.requests.get')
    def test_falha_conexao(self, get):
        get.side_effect = requests.ConnectionError('offline')
        with self.assertRaises(TraccarUnavailableError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_indisponivel(self, get):
        get.return_value = self.resposta({}, 503)
        with self.assertRaises(TraccarUnavailableError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_resposta_http_inesperada(self, get):
        get.return_value = self.resposta({}, 400)
        with self.assertRaises(TraccarResponseError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_json_invalido(self, get):
        get.return_value = self.resposta([])
        get.return_value.json.side_effect = ValueError('JSON inválido')
        with self.assertRaises(TraccarResponseError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_colecao_invalida(self, get):
        get.return_value = self.resposta({'id': 1, 'name': 'GPS'})
        with self.assertRaises(TraccarResponseError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_dispositivo_sem_id(self, get):
        get.return_value = self.resposta([{'name': 'Sem id'}])
        with self.assertRaises(TraccarResponseError):
            listar_dispositivos()

    @patch('rastreamento.services.client.requests.get')
    def test_posicao_com_coordenada_invalida(self, get):
        get.return_value = self.resposta([{'deviceId': 1, 'latitude': 130, 'longitude': 40}])
        with self.assertRaises(TraccarResponseError):
            ultimas_posicoes()

    def test_endpoint_externo_bloqueado(self):
        with self.assertRaises(ValueError):
            traccar_get('https://outro-servidor.example/api/devices')
