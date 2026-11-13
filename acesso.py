"""Porta do Calcula Cabo: a sessão só abre se o Credenciais aceitar a senha."""

import os

import requests
from flask import Flask, jsonify, redirect, request, session

APP_SLUG = "calcula_cabo"
PUBLICOS = {"/health", "/login"}


def consultar_sessao(username):
    base = os.environ.get("CREDENTIALS_URL", "").rstrip("/")
    token = os.environ.get("CREDENTIALS_API_TOKEN", "")
    if not base or not token:
        return {"ok": True, "autorizado": True}
    try:
        resposta = requests.post(
            base + "/api/sessao",
            json={"username": username, "app": APP_SLUG},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        resposta.raise_for_status()
        return resposta.json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "autorizado": False}


def consultar(username, password):
    base = os.environ.get("CREDENTIALS_URL", "").rstrip("/")
    token = os.environ.get("CREDENTIALS_API_TOKEN", "")
    if not base or not token:
        return {"ok": False, "motivo": "sem_config"}
    try:
        resposta = requests.post(
            base + "/api/verificar",
            json={"username": username, "password": password},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        resposta.raise_for_status()
        return resposta.json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "motivo": "fora"}


def proteger(server: Flask):
    server.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dev-insecure-change-me"
    server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    @server.before_request
    def _exigir_sessao():
        path = request.path
        if path in PUBLICOS or path.startswith(("/static/", "/assets/")):
            return None
        if session.get("usuario"):
            dados = consultar_sessao(session["usuario"])
            if not dados.get("ok") or not dados.get("autorizado"):
                session.clear()
                if path.startswith("/api/"):
                    return jsonify({"erro": "login"}), 401
                return redirect("/login")
            return None
        if path.startswith("/api/"):
            return jsonify({"erro": "login"}), 401
        if request.method != "GET":
            return ("login", 401)
        return redirect("/login")

    @server.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("usuario") and request.method == "GET":
            return redirect("/")
        erro = ""
        if request.method == "POST":
            nome = (request.form.get("username") or "").strip()
            senha = request.form.get("password") or ""
            resultado = consultar(nome, senha)
            if resultado.get("ok") and APP_SLUG in (resultado.get("apps") or []):
                session["usuario"] = resultado.get("username") or nome
                return redirect("/")
            if resultado.get("ok"):
                erro = _mensagem("sem_acesso")
            else:
                erro = _mensagem(resultado.get("motivo"))
        return _pagina(erro)

    @server.route("/logout")
    def logout():
        session.clear()
        return redirect("/login")


def _mensagem(motivo):
    if motivo == "trocar_senha":
        return "Troque a senha temporária no Credenciais antes de entrar aqui."
    if motivo == "sem_config":
        return "Este app ainda não está ligado ao Credenciais."
    if motivo == "fora":
        return "O Credenciais não respondeu."
    if motivo == "sem_acesso":
        return "Sua conta não tem acesso ao Calcula Cabo."
    return "Usuário ou senha inválidos."


def _pagina(erro):
    aviso = (
        '<div class="alert danger" role="status">'
        "<strong>Não foi possível entrar</strong>"
        f"<p>{erro}</p>"
        "</div>"
        if erro
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Entrar - Calcula Cabo</title>
  <link rel="icon" href="/static/images/favicon.ico">
  <link rel="stylesheet" href="/static/vendor/moya-ui/tokens.css?v=20261113e">
  <link rel="stylesheet" href="/static/vendor/moya-ui/components.css?v=20261113e">
  <link rel="stylesheet" href="/static/vendor/moya-ui/login.css?v=20261113e">
</head>
<body class="auth-body">
  <main class="auth-card">
    <div class="auth-logo">
      <img src="/static/images/moya_wordmark_official.svg" alt="Moya">
    </div>
    <h1 class="auth-title">Calcula Cabo</h1>
    <p class="auth-lead">A mesma senha dos outros sites.</p>
    {aviso}
    <form method="post">
      <div class="form-group">
        <label for="username">Usuário</label>
        <input class="input" id="username" name="username" autocomplete="username" autofocus required>
      </div>
      <div class="form-group">
        <label for="password">Senha</label>
        <input class="input" id="password" name="password" type="password" autocomplete="current-password" required>
      </div>
      <button type="submit" class="btn primary">Entrar</button>
    </form>
  </main>
</body>
</html>"""
