# Arquitetura

[← Voltar ao README](../README.md) · [Cálculo](CALCULO.md) · [Instalação](INSTALACAO.md)

> Estrutura do projeto e uso das funções de cálculo em outros scripts.

---

## Estrutura do projeto

```text
calcula_cabo/
├── calcular_bitola_cabo_dc.py   # calculadora interativa (script principal / funções de cálculo)
├── config.ini                   # constantes, tabelas e valores padrão (calibração)
├── test_calculos.py             # testes de verificação dos cálculos e do config.ini
├── app.py                       # aplicação web Flask (reaproveita as funções de cálculo)
├── templates/
│   ├── index.html               # página da interface web
│   └── memorial.html            # memorial de cálculo passo a passo
├── static/
│   ├── css/style.css            # tema escuro (identidade moya-weather-pro)
│   ├── js/app.js                # lógica da interface (fetch da API + render)
│   ├── js/memorial.js           # render do memorial e diagramas Mermaid
│   └── vendor/bootstrap/        # Bootstrap 5.3 servido localmente
├── main.py                      # ponto de entrada gerado pelo uv
├── Dockerfile                   # imagem de container (gunicorn)
├── docker-compose.yml           # build e deploy conteinerizado
├── .dockerignore
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

Para usar as funções em outro script:

```python
from calcular_bitola_cabo_dc import calcular_bitola_cb, calcular_tempo_aquecimento

resultado = calcular_bitola_cb(
    distancia=7,
    corrente=7,
    tensao=12,
    queda_percentual=5,
)
print(resultado["bitola_recomendada"], resultado["bitola_awg"])
```
