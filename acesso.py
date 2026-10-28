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
    aviso = f'<p class="erro">{erro}</p>' if erro else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Entrar - Calcula Cabo</title>
  <style>
    :root {{
      --bg-dark: #1a1d29; --bg-card: #252936; --text-primary: #ffffff;
      --text-secondary: #a8adb8; --accent-blue: #4a9eff; --accent-red: #ff6b6b;
      --border-color: #363a4a; --radius: 12px; --radius-sm: 6px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      background: var(--bg-dark); color: var(--text-primary);
    }}
    .card {{
      width: 100%; max-width: 420px; margin: 16px; padding: 40px;
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: var(--radius); box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }}
    h1 {{ text-align: center; font-size: 1.5rem; margin-bottom: 8px; }}
    .lead {{ text-align: center; color: var(--text-secondary); margin-bottom: 28px; }}
    label {{ display: block; color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px; }}
    input {{
      width: 100%; padding: 12px; margin-bottom: 18px; color: var(--text-primary);
      background: var(--bg-dark); border: 1px solid var(--border-color);
      border-radius: var(--radius-sm); font: inherit; font-size: 0.95rem;
    }}
    input:focus {{ outline: none; border-color: var(--accent-blue); }}
    button {{
      width: 100%; padding: 12px; border: none; border-radius: var(--radius-sm);
      background: var(--accent-blue); color: white; font: inherit; font-weight: 600;
      font-size: 1rem; cursor: pointer;
    }}
    button:hover {{ background: #3a8eef; }}
    .erro {{
      background: rgba(255, 107, 107, 0.1); border: 1px solid var(--accent-red);
      color: var(--accent-red); padding: 12px; border-radius: var(--radius-sm); margin-bottom: 20px;
    }}
  </style>
</head>
<body>
  <form class="card" method="post">
    <h1>Calcula Cabo</h1>
    <p class="lead">A mesma senha dos outros sites.</p>
    {aviso}
    <label for="username">Usuário</label>
    <input id="username" name="username" autocomplete="username" autofocus required>
    <label for="password">Senha</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Entrar</button>
  </form>
</body>
</html>"""
