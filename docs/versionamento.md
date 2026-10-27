# Política de versionamento

- Versionar código, configuração, documentação e pequenos casos de teste.
- Versionar em data/ somente os quatro CSVs oficiais após validação.
- Preservar uma única base oficial por versão do Git, sem cópias datadas.
- Usar data/tmp/ para saídas experimentais não versionadas.
- Versionar em reports/ apenas evidências selecionadas e revisadas.
- Usar reports/tmp/ para resultados transitórios.
- Não versionar ambientes virtuais, caches, credenciais ou arquivos temporários.
- Não versionar PBIX ou PBIT nesta etapa.
- A cópia em nuvem do PBIX e seu procedimento de atualização serão
  definidos antes da construção visual.
- Documentar versões aprovadas do PBIX e seus hashes no repositório.
- Revisar git status e o diff antes de adicionar arquivos.
- Evitar git add .; adicionar explicitamente os arquivos previstos.
- Commit registra uma versão local; push envia os commits ao GitHub.

Nenhum CSV, PBIX ou resultado de teste foi produzido por esta preparação.
