# Ordem determinística dos sorteios — versão 1

Configuração: config.json. Referência: Python 3.14.2.
Usar uma única instância local de random.Random, inicializada com a semente.
Não reiniciar a semente entre disponibilidade e chamadas.

## Disponibilidade

1. Percorrer atendentes em ordem crescente de identificador.
2. Para cada atendente, percorrer os dias em ordem cronológica.
3. Sortear um perfil com random.choices, na ordem dos perfis da configuração.
4. Para cada intervalo do perfil, sortear a fila com random.choices.
   Ordenar as filas por fila_id antes do sorteio.
5. Perfil sem disponibilidade não sorteia filas.
6. Ordenar os intervalos por atendente e início.
7. Atribuir identificadores DISP000001, DISP000002 etc.

## Chamadas — implementação posterior

Continuar usando a mesma instância aleatória após as disponibilidades.

1. Gerar primeiro uma chamada reservada por dia, em ordem cronológica.
2. Gerar depois as chamadas restantes em sequência.
3. Para cada chamada restante, sortear primeiro a data, dentre todas
   as datas em ordem cronológica, com o peso do respectivo dia da semana.
4. Para todas as chamadas, sortear nesta ordem:
   hora por random.choices; segundo dentro da hora por randint(0, 3599);
   fila por random.choices; duração do contato por randint;
   tolerância por randint; categoria de pós-atendimento por random.choices
   (zero, positivo); duração por randint somente se a categoria for positiva.
5. Todos os limites de randint são inclusivos.
6. Ordenar por entrada e sequência original antes de atribuir chamada_id.

Probabilidades não são cotas.
Alterar a ordem ou o método de sorteio exige registrar nova versão do gerador.
A repetibilidade deve ser verificada no ambiente registrado.
