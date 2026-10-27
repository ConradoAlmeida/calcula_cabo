import unittest
from unittest.mock import patch

from app import app


class PortaTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_publico(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_api_sem_sessao_recusa(self):
        resposta = self.client.post("/api/calcular", json={})
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.get_json()["erro"], "login")

    def test_pagina_sem_sessao_vai_para_o_login(self):
        resposta = self.client.get("/")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.headers["Location"].endswith("/login"))

    def test_login_aceito_abre_o_app(self):
        with patch(
            "acesso.consultar",
            return_value={"ok": True, "username": "lucas", "apps": ["calcula_cabo"]},
        ):
            resposta = self.client.post(
                "/login", data={"username": "lucas", "password": "secreta"}
            )
        self.assertEqual(resposta.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["usuario"], "lucas")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_login_sem_concessao_nao_abre(self):
        with patch(
            "acesso.consultar",
            return_value={"ok": True, "username": "lucas", "apps": ["drawings"]},
        ):
            resposta = self.client.post(
                "/login", data={"username": "lucas", "password": "secreta"}
            )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("não tem acesso", resposta.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertNotIn("usuario", sess)

    def test_senha_temporaria_nao_abre(self):
        with patch(
            "acesso.consultar", return_value={"ok": False, "motivo": "trocar_senha"}
        ):
            resposta = self.client.post(
                "/login", data={"username": "lucas", "password": "temporaria"}
            )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("temporária", resposta.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertNotIn("usuario", sess)

    def test_logout_limpa_a_sessao(self):
        with self.client.session_transaction() as sess:
            sess["usuario"] = "lucas"
        resposta = self.client.get("/logout")
        self.assertEqual(resposta.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertNotIn("usuario", sess)


if __name__ == "__main__":
    unittest.main()
