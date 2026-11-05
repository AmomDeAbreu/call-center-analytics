# Call Center Analytics v1.8 RC1 — passagem ao QA

Preparação concluída sem publicação. A decisão de aceite pertence ao QA.

## Alterações e rastreabilidade
A entrada foi preservada. Seu hash está no LEIA-ME. Havia nove divergências em relação
ao manifesto recebido: quatro arquivos locais extras e cinco arquivos alterados.
As alterações observadas foram seleções de janeiro/fevereiro/Suporte, página inicial
Atendentes e caminho pessoal. Cada divergência tem hashes e resolução registrados em
conferencias/origem_e_divergencias.json. Nenhum arquivo listado estava ausente.
Não se inferiu corrupção: os estados são compatíveis com salvamento no Desktop.
O manifesto anterior foi preservado em historico/v1_7/ e não é o manifesto atual.

Foram removidos quatro arquivos .pbi, três seleções de teste, datas residuais;
restaurada a página inicial Visão geral e neutralizado PastaDados.
Modo Between, filtro funcional, posições, fontes, cores e consultas visuais preservados.
CSV (inclusive casos), scripts de testes, DAX e demais TMDL idênticos byte a byte.
Nenhum valor esperado de teste foi alterado. Nenhuma melhoria estética foi feita.
Comparação completa de hashes em conferencias/comparacao.json.

## Execução nesta revisão
Python 3.12.14 em Linux: validador PASS, suíte 13/13, regressão SQL/estrutura 50/50.
Dez pastas controladas deram as aceitações/rejeições esperadas em Python.
Recálculo independente por timestamps confirmou global, F02, fevereiro e AT01,
inclusive tempos totais 941831, 490318, 257732 e 105938 segundos.
Logs completos contêm comandos, código de saída e resultados; inventário dos arquivos
testados permite relacionar evidências aos bytes. Não são resultados do Desktop.
Manifesto cobre todos os arquivos finais exceto ele próprio. Recibo externo acompanha
o ZIP com hash e resultado de teste de extração nova, evitando autorreferência de hash.

## Limites reais
Sem Desktop, motor M/DAX, Wine, dotnet ou endpoint Power BI acessível nesta sessão.
Aceite funcional e rejeição M: NÃO EXECUTADOS, detalhados em aceite_funcional.json.
Capturas do usuário anteriores registraram resultados corretos, mas não foram
reclassificadas como execução desta candidata final.
Gerador/configuração/suíte original não encontrados nos arquivos acessíveis;
nenhum repositório Git válido ou conector GitHub disponível. Commit desconhecido.
Regeneração, 28 testes originais, FIFO/desempates/fechamento/simultaneidade do simulador:
NÃO EXECUTADOS. O validador não substitui o simulador original.

Situação: candidata verificável preparada. Pendências: evidência de execução M/DAX
para esta candidata e reprodutibilidade original. Risco: inspeção estática/Python
não garante aceitação do projeto ou renderização no Desktop. Próximo passo: decisão
independente do QA sobre estas evidências e limitações, sem nova solicitação de testes
ao responsável. Nenhuma aprovação de publicação é declarada aqui.
