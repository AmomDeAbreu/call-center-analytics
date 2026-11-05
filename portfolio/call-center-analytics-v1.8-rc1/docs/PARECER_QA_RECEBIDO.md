# Parecer recebido — escopo de disponibilização

Fonte: parecer independente encaminhado pelo responsável na conversa em 05/11/2026.
Este arquivo é um resumo documental desse parecer, não assinatura digital nem auditoria nova.

**APROVADO COM RESSALVAS para disponibilizar no GitHub como projeto demonstrativo com validação parcial.**

O QA informou execução própria: hash correspondente; manifesto de 125 arquivos sem divergências
antes/depois; validador PASS; 13/13 testes externos; 50/50 regressão SQL/estrutura;
10/10 conjuntos controlados; recálculo dos indicadores compatível.

Também informou comparação com v1.7: CSVs, scripts de testes e expressões DAX idênticos.
Alterações funcionais limitadas a caminho da fonte, limpeza das seleções e página inicial.
Cache removido; layout e paleta preservados.

Ressalvas: simulador/configuração/suíte original ausentes; execução M/DAX e interação da candidata
final sem comprovação no Desktop; sobreposição de ocupações depende da validação Python obrigatória.
Não anunciar geração integral reproduzível, FIFO validado pelo gerador ou homologação completa.

O parecer não aprova publicação funcional no Power BI Service ou Publicar na Web.
Nenhuma publicação foi executada pelo QA. O responsável autorizou disponibilização no GitHub
dentro desse escopo; LinkedIn e outras plataformas não estão autorizados para envio automático.
