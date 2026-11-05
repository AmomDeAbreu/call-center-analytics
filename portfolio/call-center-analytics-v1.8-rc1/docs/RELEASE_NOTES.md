# Call Center Analytics v1.8 RC1 — demonstração

Projeto Power BI com 3.000 chamadas 100% sintéticas, oito atendentes, três filas e duas páginas.
Download para Power BI Desktop; não há relatório interativo hospedado nesta release.

QA: aprovado com ressalvas para disponibilização demonstrativa no GitHub, conforme parecer recebido.

Preparação auditada: CSVs, DAX, layout e paleta preservados; cache removido, parâmetro neutro,
seleções de teste limpas e Visão geral como abertura.

Evidências anteriores: manifesto 125 arquivos; validador PASS; 13/13 testes externos;
50/50 regressão SQL/estrutura; dez conjuntos controlados em Python.

Limites: gerador/configuração/suíte original indisponíveis; execução M/DAX e interação da candidata
final não comprovadas no Desktop; validação externa Python obrigatória para sobreposição de ocupações.
Não homologado para Power BI Service/Publicar na Web ou uso produtivo.

Arquivos auditados, sem recompressão:
- CallCenterAnalytics_v1_8_RC1.zip — SHA-256 741f6cbf143c5682d1fd5555d50185d51555aaccc6221c8899b05a39e332db5e
- Entrega_CallCenterAnalytics_v1_8_RC1.zip — SHA-256 1c93baad8db281dc295d63eac010e61f56e39831719c8576184a90ce075a6f7f

Consulte SHA256SUMS.txt e o README. Licenciamento não definido no pacote auditado.
