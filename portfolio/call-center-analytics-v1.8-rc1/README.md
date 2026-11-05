# Call Center Analytics

**Power BI · Power Query · DAX · Python · SQL/SQLite**

Repositório de destino: [AmomDeAbreu/call-center-analytics](https://github.com/AmomDeAbreu/call-center-analytics).

Como acompanhar demanda, abandono e tempo de atendimento em uma central de chamadas?
Este projeto demonstrativo organiza **3.000 chamadas sintéticas**, de janeiro a março de 2026,
em duas páginas: **Visão geral** e **Atendentes**. São oito profissionais e três filas.

> **Dados 100% sintéticos.** Nenhum registro representa cliente, empregador ou operação real.
> **QA: aprovado com ressalvas para disponibilização demonstrativa no GitHub**, conforme parecer
> recebido do responsável. A candidata final tem validação parcial; [consulte os limites](#validacao-e-limites).

[Baixar candidata v1.8 RC1](artifacts/CallCenterAnalytics_v1_8_RC1.zip) ·
[Entrega com evidências](artifacts/Entrega_CallCenterAnalytics_v1_8_RC1.zip) ·
[Código e modelo](demonstracao/CallCenterAnalytics_v1_8_RC1) ·
[Checksums](artifacts/SHA256SUMS.txt)

O download contém um projeto para Power BI Desktop; não é um dashboard interativo no navegador.

## Prévia do relatório

Capturas reais enviadas pelo responsável durante o desenvolvimento, reproduzidas sem edição.
Elas antecedem a candidata final: mostram filtros de data em lista, enquanto a v1.8 RC1 usa intervalo.
São prévias da apresentação, não evidência de renderização da candidata final.

### Visão geral
![Visão geral com KPIs, volume diário, volume por hora e abandono por fila](assets/visao-geral.png)

### Atendentes
![Comparação de volume e TMA de oito atendentes e detalhamento por fila](assets/atendentes.png)

## Perguntas respondidas

- Como o volume de chamadas varia por dia e hora de entrada?
- Qual é o volume atendido e abandonado em cada fila?
- Quantas chamadas são atendidas em até 20 segundos?
- Como volume e duração de atendimento variam entre profissionais, considerando a fila?

## Indicadores da base demonstrativa

| Indicador | Valor | Definição |
|---|---:|---|
| Recebidas | 3.000 | Todas as chamadas no contexto de data/fila |
| Atendidas | 1.959 | Chamadas com atendimento |
| Abandonadas | 1.041 | Chamadas sem atendimento, incluindo fechamento |
| Taxa de abandono | 34,70% | Abandonadas ÷ recebidas |
| TMA | 8,01 min | Tempo de contato + pós-atendimento ÷ atendidas; sem espera |
| SLA demonstrativo ≤ 20 s | 61,53% | 1.846 atendidas em até 20 s ÷ 3.000 recebidas |

O TMA consolidado é ponderado por chamadas. Abandonadas não são atribuídas a profissionais.
Os KPIs operacionais ignoram o filtro de atendente e preservam data/fila por definição das medidas;
a execução desse comportamento na candidata final não foi homologada.
O SLA não possui meta percentual aprovada; menor TMA não significa automaticamente melhor qualidade.
Esses valores descrevem uma simulação e não representam ganhos de uma operação real.

## Competências demonstradas

- Modelagem dimensional, relações e medidas DAX para indicadores operacionais.
- Tratamento e validações de carga em Power Query.
- Organização visual de informações em duas páginas de análise.
- Conferência dos dados com Python e consultas SQL/SQLite.
- Documentação de critérios, testes, limitações e integridade por SHA-256.

O projeto usa arquivos CSV e formatos PBIP, PBIR e TMDL. Power Automate e bancos MySQL
fazem parte da experiência declarada do responsável, mas não são dependências desta demonstração.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `artifacts/` | ZIPs auditados imutáveis e checksums |
| `demonstracao/CallCenterAnalytics_v1_8_RC1/` | Extração idêntica da candidata, para inspeção do código |
| `…/projeto/` | PBIP, relatório PBIR e modelo TMDL |
| `…/*.csv` | Quatro CSVs da base original |
| `…/validacao/` | Validador Python, testes e regressão SQL/estrutura |
| `…/casos_desktop/` | Dez fontes controladas de teste; não usar como base demonstrativa |
| `…/conferencias/` | Manifesto e registros da preparação auditada |
| `assets/` | Capturas autênticas e proveniência |
| `docs/` | Parecer recebido, notas da versão e evidências anteriores |
| `scripts/` | Verificação da publicação, separada da candidata |

## Abrir e configurar

1. Baixe o ZIP candidato e extraia em uma pasta nova.
2. Abra `CallCenterAnalytics_v1_8_RC1/projeto/CallCenterAnalytics.pbip` no Power BI Desktop
   com suporte aos formatos PBIP/PBIR/TMDL utilizados.
3. Em **Transformar dados → Gerenciar parâmetros**, configure `PastaDados` para a pasta
   que contém os quatro CSVs originais, na raiz extraída da candidata.
4. Valide os mesmos CSVs antes da atualização normal e só prossiga com resultado `PASS`:

```bash
python -B validacao/validar.py CAMINHO_DA_PASTA_DOS_CSVS
```

5. Aplique e atualize. O parâmetro distribuído usa o exemplo neutro `C:\CallCenterAnalytics\dados`.

Os comandos da candidata são executados na sua raiz extraída. Python 3.10+ e biblioteca padrão.
O ambiente das evidências anteriores usou Python 3.12.14.
Não altere o ZIP auditado. Configurar e salvar no Desktop modifica a cópia de trabalho e pode criar cache.

<a id="validacao-e-limites"></a>
## Validação e limites

Os registros da preparação anterior e o parecer independente recebido do QA relatam:

| Verificação | Resultado registrado |
|---|---|
| Manifesto da candidata | 125 arquivos; nenhuma divergência |
| Validador dos CSVs | PASS |
| Suíte externa | 13/13 |
| Regressão SQL/estrutura | 50/50 |
| Dez conjuntos controlados em Python | 10/10 com comportamento esperado |
| Recálculo independente | Indicadores globais e recortes conferem |

Fontes: [registro de execução anterior](docs/verificacao_anterior.json),
[relatório de preparação auditado](demonstracao/CallCenterAnalytics_v1_8_RC1/RELATORIO_QA.md)
e [resumo do parecer recebido](docs/PARECER_QA_RECEBIDO.md).
O relatório interno antecede o aceite do QA e permanece intacto por rastreabilidade.

**Ressalvas:**

1. Gerador, configuração e suíte original do simulador ausentes desta entrega.
   Não há comprovação de regeneração integral ou FIFO pelo gerador original.
2. M/DAX e interação da candidata final não foram executados no Desktop na preparação auditada.
   Python, SQL e inspeção textual não substituem essa execução.
3. Sobreposição de ocupações é rejeitada pelo validador Python obrigatório.
   O Desktop não executa esse validador automaticamente nem oferece bloqueio M equivalente declarado.

Escopo do aceite: projeto demonstrativo no GitHub. Não é homologação para Power BI Service
ou Publicar na Web, nem garantia de operação em produção.

Para conferir a cópia publicada, o script abaixo valida hashes, manifesto, extração e os validadores
existentes em pasta temporária, sem gravar cache na candidata:

```bash
python -B scripts/check_candidate.py
```

O workflow incluído executa a mesma conferência. A presença do arquivo de workflow não significa
que ele já tenha executado no GitHub.

## Identidade da candidata

`CallCenterAnalytics_v1_8_RC1.zip`

```text
741f6cbf143c5682d1fd5555d50185d51555aaccc6221c8899b05a39e332db5e
```

A documentação de apresentação é separada da candidata. Nenhum ZIP auditado foi recomprimido.

## Sobre o responsável

**Amom Abreu**, estudante de Engenharia de Sistemas, com experiência em Power BI,
SQL/MySQL, Power Automate e indicadores operacionais. Este projeto de portfólio demonstra
aplicações de BI e validação de dados; não representa uma entrega contratada por cliente.
Contato direto não informado nesta preparação.

## Licenciamento

Nenhuma licença de uso foi encontrada no pacote auditado. A licença do repositório de destino
ainda precisa ser verificada; esta apresentação não atribui permissões adicionais.
