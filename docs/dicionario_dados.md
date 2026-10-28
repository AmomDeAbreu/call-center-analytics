# Dicionário de dados — Call Center Analytics

Status: especificação documental aprovada; implementação e dados ainda não validados.
Configuração de referência: config.json, versão 1.0.0.
Regras complementares: regras_simulacao.md.

## Convenções

- Dados exclusivamente sintéticos.
- CSV UTF-8, separador vírgula, cabeçalho e quebras de linha LF.
- Identificadores textuais; durações inteiras em segundos.
- Data/hora: AAAA-MM-DD HH:MM:SS, precisão de segundos.
- Horário local de Brasília, UTC-03:00, conforme configuração.
- Célula vazia representa nulo; não utilizar as palavras "null" ou "None".
- Limites numéricos são inclusivos, exceto quando indicado.
- Nenhuma correção, exclusão ou deduplicação silenciosa é permitida.
- Datas analíticas representam a entrada, não a distribuição do trabalho no tempo.

## chamadas.csv

Granularidade: uma chamada finalizada.
Volume: 3.000 registros, com entrada nos 90 dias de 01/01/2026 a 31/03/2026.

| Coluna | Tipo | Descrição | Obrigatoriedade | Valores e consistência | Relacionamento |
|---|---|---|---|---|---|
| chamada_id | Texto | Identificador da chamada | Sempre | CH000001 a CH003000; único | Chave primária |
| fila_id | Texto | Fila de entrada, sem transferência | Sempre | F01, F02 ou F03 | filas.fila_id |
| entrada_em | Data/hora | Entrada na fila | Sempre | Período aprovado; 08h inclusive até 18h exclusive | Origina data_entrada |
| status | Texto | Desfecho | Sempre | ATENDIDA ou ABANDONADA | — |
| atendente_id | Texto | Profissional que atendeu | Atendidas; nulo nas abandonadas | AT01 a AT08 | atendentes.atendente_id |
| disponibilidade_id | Texto | Intervalo utilizado | Atendidas; nulo nas abandonadas | Deve pertencer ao mesmo atendente e à mesma fila | disponibilidade_atendentes.disponibilidade_id |
| inicio_atendimento_em | Data/hora | Início do contato | Atendidas; nulo nas abandonadas | >= entrada; antes das 18h; <= limite individual de tolerância | Dentro da disponibilidade vinculada |
| saida_em | Data/hora | Fim do contato ou saída da fila sem atendimento | Sempre | Mesmo dia da entrada; atendida: > início; abandonada: > entrada e <= 18h | — |
| pos_atendimento_segundos | Inteiro | Pós-atendimento efetivamente realizado | Atendidas; nulo nas abandonadas | 0 a 180; igual ao planejado quando atendida | — |
| tolerancia_espera_segundos | Inteiro | Tolerância sorteada | Sempre | 5 a 600; fechamento pode encurtar espera efetiva | — |
| duracao_contato_planejada_segundos | Inteiro | Duração sorteada para verificar elegibilidade | Sempre | F01: 30–300; F02: 180–1200; F03: 120–900 | Regra por fila |
| pos_atendimento_planejado_segundos | Inteiro | Pós-atendimento sorteado | Sempre | 0 a 180 | — |
| motivo_abandono | Texto | Motivo da saída sem atendimento | Abandonadas; nulo nas atendidas | DESISTENCIA ou FECHAMENTO | Regras de eventos |

Nas atendidas, saída menos início deve coincidir com a duração planejada.
Nas abandonadas, tempos planejados não representam trabalho realizado.
Os campos planejados são de auditoria: não entram no TMA nem nos visuais de uso comum.

## atendentes.csv

Granularidade: um profissional fictício; exatamente oito registros.

| Coluna | Tipo | Descrição | Obrigatoriedade | Valores e consistência | Relacionamento |
|---|---|---|---|---|---|
| atendente_id | Texto | Identificador | Sempre | AT01 a AT08; único | Chave primária |
| atendente_nome | Texto | Nome fictício de exibição | Sempre | Atendente 01 a Atendente 08; correspondência estável com ID | — |

Não há fila fixa por profissional.
NAO_ATRIBUIDO será acrescentado somente à dimensão no Power BI.
Esse registro técnico não é um nono profissional.
Somente abandonadas válidas podem receber esse mapeamento na importação.
Atendida sem profissional é erro.

## filas.csv

Granularidade: uma fila; exatamente três registros.

| Coluna | Tipo | Descrição | Obrigatoriedade | Valores e consistência | Relacionamento |
|---|---|---|---|---|---|
| fila_id | Texto | Identificador | Sempre | F01, F02, F03; único | Chave primária |
| fila_nome | Texto | Nome da fila | Sempre | F01 = Informações; F02 = Suporte; F03 = Financeiro | — |

## disponibilidade_atendentes.csv

Granularidade: intervalo contínuo de alocação de um profissional a uma fila.
Quantidade variável, determinada pela configuração e pela semente.

| Coluna | Tipo | Descrição | Obrigatoriedade | Valores e consistência | Relacionamento |
|---|---|---|---|---|---|
| disponibilidade_id | Texto | Identificador do intervalo | Sempre | DISP seguido de sequência numérica; único e determinístico | Chave primária |
| atendente_id | Texto | Profissional alocado | Sempre | AT01 a AT08 | atendentes.atendente_id |
| fila_id | Texto | Fila da alocação | Sempre | F01, F02 ou F03 | filas.fila_id |
| inicio_disponibilidade_em | Data/hora | Início do intervalo | Sempre | Nos 90 dias; >= 08h e < 18h | — |
| fim_disponibilidade_em | Data/hora | Limite para concluir a ocupação | Sempre | > início; mesma data; <= 18h30 | — |

Disponibilidade não significa ociosidade.
Pausas e folgas são ausência de intervalos, sem motivos inventados.
Intervalos do mesmo profissional não podem se sobrepor, inclusive entre filas.
Adjacência é permitida, mas um atendimento não pode atravessar dois intervalos.
A entrada da chamada pode anteceder o início da disponibilidade.

## Campos derivados no Power Query

| Campo | Tipo | Regra |
|---|---|---|
| data_entrada | Data | Data de entrada_em |
| hora_entrada | Inteiro | Hora de entrada_em, de 8 a 17 |
| espera_segundos | Inteiro | Atendida: início - entrada; abandonada: saída - entrada |
| duracao_atendimento_segundos | Inteiro | Saída - início nas atendidas; nulo nas abandonadas |
| tempo_total_atendimento_segundos | Inteiro | Contato + pós-atendimento nas atendidas; nulo nas abandonadas |
| fim_pos_atendimento_em | Data/hora | Saída + pós-atendimento nas atendidas; nulo nas abandonadas |
| atendida_ate_20s | Lógico | Status ATENDIDA e espera <= 20 segundos |

O controle independente recalculará essas informações a partir da origem.

## Modelo analítico

- DimData: calendário contínuo de 01/01/2026 a 31/03/2026.
- Relações ativas 1:N, unidirecionais, dimensão para FatoChamadas.
- DimData relaciona-se por data_entrada.
- DimFila relaciona-se por fila_id.
- DimAtendente relaciona-se pela chave tratada no Power Query.
- Disponibilidade é fonte de auditoria, sem segundo caminho de filtros na fato.
- Toda chave da fato deve encontrar correspondência na respectiva dimensão.
