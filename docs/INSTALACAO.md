# Instalação

[← Voltar ao README](../README.md) · [Operação](OPERACAO.md) · [Cálculo](CALCULO.md)

> Requisitos, execução local, interface web, acesso pelo Credenciais e Docker.

---

## Requisitos

- Python **3.14** ou superior (definido em `pyproject.toml`)
- Nenhuma dependência externa

O projeto usa o gerenciador [uv](https://docs.astral.sh/uv/), mas o script principal também pode ser executado com o Python do sistema.

## Como executar

### Com uv

```bash
uv run python calcular_bitola_cabo_dc.py
```

### Com Python

```bash
python calcular_bitola_cabo_dc.py
```

O programa é interativo. Basta responder às perguntas no terminal. Se um campo for deixado em branco, o valor padrão é usado.

## Interface web

Além da CLI, o projeto oferece uma interface web (Flask + [Bootstrap 5.3](https://getbootstrap.com/)) que reaproveita as mesmas funções de cálculo. A aplicação Flask fica em `app.py`.

### Executar em desenvolvimento

```bash
uv run python app.py
```

A aplicação sobe em `http://localhost:8000` (a porta pode ser alterada com a variável de ambiente `PORT`).

### Executar em produção (gunicorn)

```bash
uv run gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

## Acesso pelo Credenciais

O app é standalone, mas usa a senha única do moyaserver. Configure no `.env`:

```text
CREDENTIALS_URL=http://moya-credenciais:8080
CREDENTIALS_API_TOKEN=o mesmo token do Credenciais
FLASK_SECRET_KEY=uma chave estável
```

O container precisa estar na rede Docker `moya`.
A pessoa só entra se tiver a concessão `calcula_cabo` no Credenciais.

O Bootstrap é servido localmente (`static/vendor/bootstrap/`), então a interface funciona sem acesso à internet.

## Docker

```bash
docker compose up -d --build
```

Acessar em `http://<ip-do-host>:8000`.

O `config.ini` do host é montado no container (somente leitura). Edite-o para recalibrar sem rebuild.

### moyaserver (produção)

Repositório espelhado no Gitea: `ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git`  
(mirror read-only do GitHub; o push de desenvolvimento vai para `origin` no GitHub.)

Fluxo:

1. **Development:** `git push origin master` (GitHub)
2. **Gitea:** sincroniza o mirror (automático ou manual em *Sync Mirror* no Gitea)
3. **moyaserver:** `git pull` + rebuild abaixo

A porta **8000** do host já é usada pelo Portainer; use o overlay `docker-compose.moya.yml` (publica em **8030**):

```bash
git clone ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git
cd calcula_cabo
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

Atualizar:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

Após push no GitHub, aguarde o mirror do Gitea ou dispare *Sync Mirror* antes do `git pull` no servidor.

Acesso interno: `http://moya-calcula-cabo.local` (via Caddy no moyaserver).

### Build manual (sem Compose)

```bash
docker build -t calcula-cabo .
docker run --rm -p 8000:8000 -v ./config.ini:/app/config.ini:ro calcula-cabo
```
