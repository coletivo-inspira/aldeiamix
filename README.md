# Aldeia MIX

Site: https://coletivo-inspira.github.io/aldeiamix/

## Publicar uma edição

1. Na [biblioteca do Drive](https://drive.google.com/drive/folders/1HskEIFh64u0phtkLSJ97Ki3L7uRpRrJb), crie uma subpasta por evento e envie suas fotos (JPEG, PNG ou WebP, até 25 MB cada) e vídeos MP4. Não use atalhos para outras pastas. Mantenha as mídias diretamente na pasta do evento.
2. Abra a [planilha Edições Aldeia MIX](https://docs.google.com/spreadsheets/d/1D3cqpvJzfX5owavS9Sco1Qpt7SO_xa4rSlsNdRX88pk/edit). Na aba **Edições**, acrescente uma linha. Use um `id` estável em letras minúsculas, números e hífens, nome, data `AAAA-MM-DD`, descrição e link da pasta.
3. Para escolher a capa, cole em `capa` o link de uma imagem da mesma pasta. Em branco, usa a primeira foto por ordem de nome. Prefixos `01-`, `02-` organizam a galeria.
4. Em `publicar`, escreva **SIM**. **NÃO** ou célula vazia mantém a linha fora do catálogo. A galeria pública mostra apenas eventos já realizados, considerando São Paulo.
5. Depois de conectar o Google, alterações são publicadas a cada hora (minuto 23; o GitHub pode atrasar). Para antecipar, execute **Actions → Publish GitHub Pages → Run workflow**. Remover uma foto ou marcar NÃO remove o conteúdo na próxima publicação bem-sucedida.

Vídeos usam o visualizador do Drive e devem ter acesso de leitura para qualquer pessoa com o link. Eles só carregam depois de clicar em Assistir. O site não importa posts do Instagram.

## Ativar a conexão Google (pendente)

O site inicia com uma biblioteca vazia. O agendamento está preparado, mas fica suspenso até a conexão ser ativada.

1. Em um projeto Google Cloud, habilite **Google Drive API** e **Google Sheets API**.
2. Crie uma conta de serviço exclusiva para a biblioteca, sem papéis administrativos no projeto. Compartilhe somente a pasta acima com o e-mail da conta, como **Leitor**. Não conceda delegação de domínio.
3. Crie a credencial JSON dessa conta. Em **GitHub → Settings → Secrets and variables → Actions → Secrets**, salve o JSON no segredo `GOOGLE_SERVICE_ACCOUNT_JSON`. Nunca envie a chave no chat nem adicione o arquivo ao repositório. Guarde e rotacione a credencial conforme a política da organização.
4. Em **Variables**, defina `DRIVE_SYNC_ENABLED` como `true`. Execute o workflow manualmente e confirme sucesso antes de considerar a sincronização ativa.
5. Depois da primeira importação, mantenha essa variável ativa. Para pausar, desative o workflow no GitHub; não remova a variável, pois o modo inicial publica uma biblioteca vazia.

Se a configuração ou a leitura falhar com a sincronização ativa, o workflow falha antes do deploy e a versão pública anterior permanece. O GitHub Actions mostra o diagnóstico; não se substitui falha por catálogo vazio. A biblioteca vazia inicial é publicada apenas no modo explícito de preparação.

## Implementação

- `library.json` identifica a única biblioteca e planilha autorizadas. Credenciais não fazem parte do catálogo.
- O importador valida as linhas, a ancestralidade das pastas, os tipos de arquivo, capas e acesso público dos vídeos. Lê todas as páginas de resultados. Pastas aninhadas podem representar uma edição; atalhos não são seguidos.
- Fotos são convertidas para WebP com dimensão máxima de 1920 px e sem metadados EXIF. Mídias só existem no artefato de deploy, sem commits dos originais.
- `data/editions.json` é a interface pública: `version`, `updatedAt` opcional e `editions[]` com `id`, `name`, `date`, `description`, `cover` e `media[]`. Fotos têm `src`, `alt`, `width`, `height`; vídeos têm `preview` e `url`.
- URLs de edição: `edicoes.html?id=identificador`. Conteúdo textual é inserido com `textContent`.

## Verificação local

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/catalog.test.mjs
python scripts/sync_drive.py --bootstrap-empty
python -m http.server 8765 --directory _site
```

Para validar com a biblioteca real, configure o segredo no ambiente de execução e remova `--bootstrap-empty`. Nunca imprima a credencial. Os testes usam dados sintéticos locais; nenhum evento fictício é publicado.
