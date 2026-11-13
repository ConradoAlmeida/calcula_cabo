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

O GitHub é a fonte de desenvolvimento; o Gitea é um mirror read-only em
`ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git`. O push vai para
`origin` no GitHub e o servidor também puxa de `origin` (GitHub).

Fluxo:

1. **Development:** `git push origin master` (GitHub)
2. **moyaserver:** `git pull origin master` + rebuild abaixo
3. **Gitea:** mirror opcional para consulta; sincroniza no intervalo dele ou em *Sync Mirror*

A porta **8000** do host já é usada pelo Portainer; use o overlay `docker-compose.moya.yml` (publica em **8030**):

```bash
git clone https://github.com/ConradoAlmeida/calcula_cabo.git
cd calcula_cabo
git remote add gitea ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

Atualizar:

```bash
git pull origin master
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

O deploy não depende do mirror do Gitea. Se quiser atualizar o mirror para
consulta, use *Sync Mirror* no Gitea.

Acesso interno: `http://moya-calcula-cabo.local` (via Caddy no moyaserver).

### Build manual (sem Compose)

```bash
docker build -t calcula-cabo .
docker run --rm -p 8000:8000 -v ./config.ini:/app/config.ini:ro calcula-cabo
```
