# Regras da simulação — Call Center Analytics

Status: desenho aprovado; gerador, dados e indicadores ainda não validados.
Parâmetros numéricos: config.json, versão 1.0.0.
Campos: dicionario_dados.md.

## 1. Limites e interpretação

Operação demonstrativa de baixo volume: 3.000 chamadas, oito atendentes,
três filas e 90 dias. Sem transferências, interrupções ou múltiplos
atendentes por chamada.

Probabilidades orientam sorteios, não são cotas.
Uma chamada reservada por dia garante cobertura diária e altera ligeiramente
a distribuição final entre dias úteis e fins de semana.
As outras 2.910 chamadas têm datas sorteadas com os pesos configurados.
Todas as chamadas usam os pesos de hora; dentro da hora, o segundo é
uniforme de 0 a 3599.

Filas são sorteadas pelos pesos configurados.
Contato e tolerância usam inteiros uniformes nos intervalos configurados.
Pós-atendimento: peso 15 para zero e 85 para inteiro uniforme de 1 a 180.
Para cada atendente e dia, sortear um perfil de disponibilidade.
Para cada intervalo do perfil, sortear uma fila pelos pesos configurados.

Ausência de cobertura pode causar abandono mesmo sem excesso de demanda.
Diferenças de TMA entre profissionais precisam considerar as filas atendidas.
A escala é sintética; não é proposta de dimensionamento ou escala trabalhista.

## 2. Ocupação e elegibilidade

Ocupação = [início do atendimento, saída + pós-atendimento).
Um próximo atendimento pode começar exatamente no fim dessa ocupação.

Exigir:
início da disponibilidade <= início do atendimento < saída
<= fim do pós-atendimento <= fim da disponibilidade.

Contato e pós-atendimento devem caber em um único intervalo.
Não combinar intervalos adjacentes.
Disponibilidade e ocupação não podem se sobrepor por profissional,
inclusive entre filas diferentes.
Validar a integridade das disponibilidades antes de simular.

Um profissional é elegível quando está livre, alocado à fila,
e comporta a ocupação completa no intervalo atual.
A duração planejada é conhecida antes da atribuição: simplificação explícita.

Entre elegíveis, escolher quem está livre há mais tempo no intervalo atual.
A contagem começa no início do intervalo; após atendimento, no fim do
pós-atendimento. Reinicia em cada intervalo, inclusive após troca de fila.
Desempate: menor atendente_id.

## 3. FIFO e eventos simultâneos

FIFO estrito por fila, ordenado por entrada_em e chamada_id.
Somente a primeira chamada pode ser atribuída.
Se ela não cabe, bloqueia as posteriores até atendimento ou abandono.
Chamadas posteriores continuam sujeitas às próprias tolerâncias.

Eventos: chegada, início/fim de disponibilidade, fim da ocupação,
expiração individual de tolerância e fechamento.

Para cada instante t anterior às 18h:
1. Atualizar disponibilidades e liberações e inserir todas as chegadas em t.
2. Processar F01, F02 e F03 em ordem estável.
3. Em cada fila, examinar a primeira chamada:
   - Se elegível, atribuir em t e reavaliar imediatamente a próxima.
   - Se não elegível e o prazo termina em t, registrar DESISTENCIA,
     remover e reavaliar imediatamente a próxima.
   - Se não elegível e o prazo é futuro, manter a primeira e registrar
     desistências das posteriores que expiram em t, sem ultrapassagem.
4. Concluir o instante apenas quando não houver novas atribuições
   ou desistências possíveis.

Prazo individual = entrada + tolerância.
Atendimento no prazo exato tem precedência sobre desistência antes das 18h.
Uma chamada com prazo anterior a t ainda na fila constitui erro.
Expirações devem ser processadas mesmo sem outro evento simultâneo.

Às 18h: nenhuma nova atribuição. Todas as chamadas ainda esperando
saem com motivo FECHAMENTO, inclusive as que expiram exatamente às 18h.
DESISTENCIA ocorre no prazo individual, estritamente antes das 18h.
Não antecipar desistência por conhecer ausência futura de atendimento.

Após 18h, continuar acompanhando ocupações e liberações até terminarem,
no máximo às 18h30. Fim do contato não libera quem ainda faz pós-atendimento.

## 4. Indicadores e filtros

Recebidas = linhas da base integralmente validada, com IDs únicos.
Atendidas = quantidade com status ATENDIDA.
Abandono = abandonadas / recebidas.
TMA = soma de contato e pós-atendimento efetivos / atendidas.
SLA = atendidas com espera <= 20 segundos / recebidas.

SLA é regra demonstrativa, não padrão universal.
Seu denominador inclui abandonos curtos e fechamento.
Abandono inclui DESISTENCIA e FECHAMENTO.
Tempos planejados de abandonadas não representam trabalho e não entram no TMA.

Página operacional: os cinco KPIs ignoram atendente e respeitam
data, hora de entrada e fila. Sem segmentação por atendente.
Página de atendentes: somente atendidas e TMA, com medidas próprias
que respondem a atendente, data, hora de entrada e fila.
Não oferecer filtro de status que altere silenciosamente os denominadores.

Sem chamadas: contagens zero, taxas vazias e TMA vazio.
Sem atendidas: TMA vazio.
Somente abandonadas: abandono 100%, SLA 0%, TMA vazio.
Exibir vazio como travessão.
Totais recalculados por somas e contagens, sem média simples de médias
ou percentuais parciais.

## 5. Reprodutibilidade

Usar gerador aleatório local com semente fixa, sem dependência do relógio.
Fixar a ordem dos sorteios no código e documentá-la antes da primeira geração.
Ordenar chamadas por entrada e sequência original do sorteio antes dos IDs.
Ordenar disponibilidades por atendente e início antes dos IDs.

Mesma versão do gerador, configuração e ambiente deve produzir os mesmos CSVs.
Fixar ordem de colunas e linhas, UTF-8, LF e formato de datas.
Não inserir horário de execução no conteúdo dos CSVs.
Comparar hashes de duas execuções equivalentes.
Registrar versão do código, Python e hash da configuração nas evidências.

Não trocar sementes, retentar configurações ou editar linhas silenciosamente.
Se cobertura falhar, registrar e submeter a alteração antes de regenerar.

## 6. Validação independente

O controle pode compartilhar dados e configuração, mas não a função
de decisão de atribuição do gerador.
Gerador por eventos; controle independente segundo a segundo.

Comparar chamada_id, status, atendente_id, disponibilidade_id,
início, saída, motivo de abandono e fim da ocupação.
Conferir decisões FIFO e oportunidades de atendimento, além de integridade.
Nenhuma violação pode ser escondida por deduplicação ou descarte.
Mapear NAO_ATRIBUIDO somente para abandonadas válidas.

## 7. Cobertura da base oficial

- Exatamente 3.000 chamadas, oito profissionais e três filas.
- Ao menos uma entrada em cada um dos 90 dias.
- Todas as filas com atendidas e abandonadas.
- Todos os profissionais com ao menos um atendimento.
- Atendidas com espera <= 20 segundos e > 20 segundos.
- Abandonos por DESISTENCIA e FECHAMENTO.
- Pós-atendimento positivo e disponibilidade variável.
- Nenhuma meta artificial de bom SLA ou baixo abandono.

## 8. Casos obrigatórios de teste

- Duplicidade, chave inexistente, nulo indevido, tipo ou status inválido.
- Disponibilidade de outro profissional ou outra fila.
- Ocupação atravessando intervalos ou ultrapassando seu fim.
- Sobreposição de um segundo e adjacência exata; também entre filas.
- Entrada às 08h aceita; entrada ou início às 18h rejeitados.
- Trabalho terminando no limite aceito; um segundo além rejeitado.
- Contato e pós-atendimento fora dos limites rejeitados.
- Duas chamadas no prazo com dois elegíveis: ambas atendidas em t.
- Primeira não cabe e expira; segunda cabe e expira: primeira desiste,
  segunda é atendida em t.
- Primeira com prazo futuro; segunda expira: segunda desiste.
- Expiração sem outro evento: saída exatamente no prazo.
- Liberação às 18h: sem nova atribuição; fechamento prevalece.
- Atendimento iniciado antes das 18h acompanhado até a liberação.
- Esperas de 20 e 21 segundos e contextos vazios.
- Grupos de tamanhos diferentes para detectar média de médias.
- Seleção de um ou vários atendentes e contextos das duas páginas.
- Duas gerações equivalentes com hashes iguais.
- Validador rejeitando deliberadamente casos inválidos.

Caso manual: quatro chamadas, duas atendidas com esperas 20 e 21 segundos,
contatos 60 e 120 segundos e pós-atendimentos 0 e 30; duas abandonadas.
Esperado: recebidas 4, atendidas 2, abandono 50%, TMA 105 segundos, SLA 25%.
Montar horários e disponibilidades válidos para esse caso.

Conferência Python versus Power BI:
contagens exatas; diferença inferior a 0,01 segundo no TMA e
0,01 ponto percentual nas taxas, antes da formatação.
Também conferir total geral e recortes de data e fila.

Esses casos são requisitos: nenhum resultado de teste é afirmado aqui.
