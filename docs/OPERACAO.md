# Operação

[← Voltar ao README](../README.md) · [Instalação](INSTALACAO.md) · [Cálculo](CALCULO.md)

> Endpoints da API, relatório TXT e exemplo de uso.

---

## Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/` | Página com o formulário e os resultados. |
| `GET` | `/health` | Verificação de saúde (`{"status": "ok"}`). |
| `POST` | `/api/calcular` | Recebe os parâmetros em JSON e devolve o dimensionamento e a análise térmica. |
| `POST` | `/api/relatorio` | Gera e devolve o relatório `.txt` para download. |
| `GET` | `/api/config` | Devolve a configuração/calibração ativa (constantes, tabelas e padrões) para conferência. |

Todas as rotas exigem login no Credenciais, exceto `/health` e `/login`.
A API (`/api/*`) responde `401` em JSON quando não há sessão.

## Relatório em TXT

Se você escolher salvar o relatório, o arquivo é gerado no diretório atual com um nome estável baseado nos parâmetros, por exemplo:

```text
relatorio_bitola_dc_d7_i7_v12_q5_ta25_tm200_deestimado_refsim_7dd0effa.txt
```

Se já existir um relatório com a mesma combinação de entradas, o programa pergunta se deseja reutilizar o arquivo sem recalcular.

O TXT contém:

1. dados de entrada
2. resumo executivo
3. tabela de dimensionamento
4. análise térmica comparativa
5. tabela de referência (opcional)

## Exemplo

Para 7 m, 7 A, 12 V DC e queda máxima de 5%:

| Seção calculada | Bitola recomendada | AWG | Queda T. final | Status |
| --- | --- | --- | --- | --- |
| 2,86 mm² | 4,00 mm² | 12 | 0,43 V (3,57%) | APROVADO |
