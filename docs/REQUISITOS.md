# Documento de Requisitos — Sistema de Gerenciamento Multimídia (SGM)

> **Disciplina:** Tópicos em Engenharia de Software (Engenharia de Software aplicada à AWS) — UFPI
> **Base:** Especificação de Requisitos de Software (ERS) do SGM, fornecida pelo professor. A numeração RF-x.y é a da ERS.
> **Sprint:** 2 (protótipo 2), de 26/11 a 09/12/2026. Backlog: issues #62 a #91 e #26.
> **Relacionados:** [`ARQUITETURA.md`](ARQUITETURA.md) (como cada requisito é atendido, ADRs) e `TESTES.md` (estratégia e resultados, issue #89).

---

## Sumário

1. Objetivo e escopo
2. Atores
3. Glossário
4. Requisitos funcionais
5. Propriedades dos objetos
6. Formatos suportados
7. Regras de negócio
8. Requisitos não funcionais (mensuráveis)
9. Interpretações e decisões
10. Fora do escopo
11. Matriz de rastreabilidade

---

## 1. Objetivo e escopo

O SGM é uma aplicação web em que cada usuário guarda, organiza, pesquisa e reproduz as **próprias** imagens, áudios e vídeos, com uma interface no estilo de um "drive" na nuvem.

O SGM evolui o protótipo 1 (cadastro, login, perfil e imagem de perfil), que continua valendo sem mudanças de comportamento. A sprint 2 acrescenta:

- upload de arquivos multimídia direto para o S3, com cota de 100 MB por usuário;
- processamento automático: miniaturas e propriedades de imagens; propriedades, miniatura e versões 1080p/720p/480p de vídeos; propriedades de áudios;
- listagem, pesquisa, filtros, visualização, edição e exclusão dos objetos;
- infraestrutura escalável na AWS: CloudFront, Application Load Balancer, Auto Scaling da aplicação e dos workers, fila SQS.

## 2. Atores

| Ator | Descrição |
|---|---|
| Visitante | Pessoa não autenticada. Só pode se cadastrar e entrar |
| Usuário | Pessoa autenticada. Gerencia o próprio perfil e os próprios objetos; nunca vê objetos de outro usuário |
| Worker de processamento | Componente do sistema (ator secundário) que consome a fila e processa áudios e vídeos em segundo plano |
| Operador | Membro da equipe que implanta e acompanha a aplicação na AWS (deploy, escala, custos) |

## 3. Glossário

| Termo | Significado |
|---|---|
| Objeto / arquivo | Uma imagem, um áudio ou um vídeo enviado por um usuário, com seus metadados |
| Original | O arquivo exatamente como foi enviado. É o único que conta na cota |
| Miniatura | Imagem reduzida usada em listagens e como pôster do vídeo |
| Versão | Cópia de um vídeo numa qualidade (1080p, 720p, 480p), associada ao original |
| Cota | Espaço máximo de originais por usuário: 100 MB (104 857 600 bytes) |
| URL pré-assinada | Endereço temporário, assinado pela aplicação, que dá acesso a um objeto privado do S3 por tempo limitado |
| Fila | Fila SQS onde a aplicação deixa os pedidos de processamento de áudio e vídeo |
| DLQ | Fila de mensagens que falharam repetidamente (*dead-letter queue*) |
| Status | Situação do objeto: `pending_upload` → `queued` → `processing` → `ready` ou `failed` |

## 4. Requisitos funcionais

Prioridade: **O** = obrigatório (ERS), **D** = desejável. Issues da sprint 1 aparecem quando o requisito já foi entregue lá.

### 4.1 Gerenciamento de usuários (ERS 3.1)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-1.1 | O sistema deve permitir que os usuários se registrem e criem novas contas | O | Cadastro com nome completo, username, email, senha e descrição opcional cria a conta; email ou username repetido é recusado com mensagem no campo | Sprint 1 (#8, #13); sem mudança |
| RF-1.2 | O sistema deve autenticar os usuários por meio de credenciais de login (username e senha) | O | Login por username ou email + senha abre a sessão; credenciais erradas dão mensagem genérica; rotas protegidas exigem sessão; logout invalida a sessão. Tudo funciona pelo endereço HTTPS da CloudFront | Sprint 1 (#7, #9, #12, #13); #84 |
| RF-1.3 | O sistema deve permitir que usuários autorizados gerenciem seus perfis (editar informações, alterar senha) | O | Edição de nome, username, email, descrição e imagem de perfil; troca de senha conferindo a atual. A imagem de perfil passa a ficar em `users/{uid}/profile/` | Sprint 1 (#10, #11, #15, #16); #67, #79 |

### 4.2 Gerenciamento de objetos multimídia (ERS 3.2)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-2.1 | O sistema deve permitir que usuários autorizados façam upload de imagens, áudios e vídeos nos formatos da seção 6 | O | Arquivo de cada formato suportado é aceito e aparece na listagem; arquivo de outro tipo é recusado (422 `UNSUPPORTED_FILE`); arquivo acima da cota restante é recusado (413 `QUOTA_EXCEEDED`); o painel de envio mostra o progresso | #66, #67, #69, #76, #79 |
| RF-2.2 | O sistema deve armazenar os objetos carregados com segurança | O | Bucket privado (Block Public Access); acesso direto ao objeto sem assinatura → `AccessDenied`; leitura só por URL pré-assinada de até 1 h, gerada para o dono; criptografia em repouso (SSE-S3) | #67, #79, #81 |
| RF-2.3 | O sistema deve permitir que usuários autorizados visualizem objetos existentes | O | O usuário abre qualquer objeto próprio e vê o conteúdo e as propriedades (RF-5.2) | #70, #77 |
| RF-2.4 | O sistema deve permitir que usuários autorizados editem informações e conteúdo de objetos (renomear, atualizar descrição, adicionar tags) | O | Nome, descrição, tags e gênero (áudio e vídeo) são editáveis e persistem; as mudanças passam a valer na pesquisa. Ver interpretação em 9.1 | #70, #77 |
| RF-2.5 | O sistema deve permitir que usuários autorizados excluam objetos | O | Após confirmar, o objeto some da listagem; original, miniatura e versões são apagados do S3; a cota usada diminui do tamanho do original | #70, #77 |

### 4.3 Processamento de imagens (ERS 3.2.1)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-2.6 | Após o upload de uma imagem, o sistema deve gerar automaticamente uma miniatura | O | Ao concluir o upload, a imagem já volta com status `ready`, miniatura e propriedades da seção 5.2 (RNF-03) | #68, #69 |
| RF-2.7 | A miniatura deve ser usada em listagens e outros contextos de visualização | O | A grade do "Meu Drive" carrega a miniatura, não o original | #70, #75 |

### 4.4 Processamento de vídeos (ERS 3.2.2)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-2.8 | Após o upload de um vídeo, o sistema deve gerar uma miniatura a partir do primeiro quadro | O | Depois do processamento, o vídeo tem miniatura igual ao 1º quadro | #72, #73 |
| RF-2.9 | A miniatura do vídeo deve ser usada em listagens e visualizações | O | A grade mostra a miniatura do vídeo; o player a usa como pôster | #75, #78 |
| RF-2.10 | O sistema deve criar versões do vídeo em 1080p, 720p e 480p | O | Um vídeo 1080p enviado termina com as três versões, todas reproduzíveis no navegador; um vídeo menor recebe só as versões sem ampliação (RN-04) | #72, #73, #86 |
| RF-2.11 | Cada versão deve ficar associada ao original e o usuário deve poder escolher a qualidade na reprodução; o padrão é 1080p | O | O detalhe do vídeo lista as versões; o player abre na maior versão ≤ 1080p e troca de qualidade mantendo a posição | #70, #78 |

### 4.5 Processamento de áudios (ERS 3.2.2, "Processamento de Áudio")

A ERS lista as propriedades do áudio sem numerar um requisito. Para manter a rastreabilidade, a equipe usa o ID abaixo.

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-2.12 | Após o upload de um áudio, o sistema deve extrair as propriedades da seção 5.4 | O | Depois do processamento, o áudio mostra duração, taxa de bits, taxa de amostragem e canais, e toca no player do navegador | #72, #74 |

### 4.6 Pesquisa (ERS 3.3)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-3.1 | Pesquisar objetos por palavras-chave na descrição, no nome e nas tags | O | "praia" encontra objetos com "Praia" no nome, "fotos da praia" na descrição ou a tag `praia`; a busca ignora maiúsculas e acentos ("cancao" acha "Canção") | #70, #75 |
| RF-3.2 | Exibir os resultados conforme as palavras-chave inseridas | O | A grade mostra só os resultados, com estado "nenhum resultado" quando vazia | #75 |

### 4.7 Listagem (ERS 3.4)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-4.1 | Listar todos os objetos | O | "Meu Drive" lista todos os objetos do usuário, paginados (até 50 por página), dos mais novos para os mais antigos | #70, #75 |
| RF-4.2 | Listar objetos por tipo (imagens, áudios, vídeos) | O | Os itens "Imagens", "Áudios" e "Vídeos" da barra lateral filtram a grade | #66, #70, #75 |
| RF-4.3 | Combinar palavras-chave com os filtros de listagem | O | Tipo e pesquisa juntos (ex.: vídeos com "aula") retornam a interseção; o filtro fica na URL (`?type=video&q=aula`) | #70, #75 |

### 4.8 Visualização (ERS 3.5)

| ID | Requisito | Prio. | Critério de aceite | Issues |
|---|---|---|---|---|
| RF-5.1 | Selecionar um objeto de uma lista | O | Clicar num item da grade abre `/dashboard/files/:id` | #75, #77 |
| RF-5.2 | Exibir o conteúdo e os detalhes do objeto conforme o tipo | O | Imagem é exibida; áudio toca em `<audio>`; vídeo toca em `<video>` com seleção de qualidade; todas as propriedades da seção 5 aparecem; objeto ainda em processamento mostra o status | #77, #78 |

## 5. Propriedades dos objetos

Origem: **S** = extraída ou gerada pelo sistema; **U** = definida pelo usuário. Tabelas conforme a ARQUITETURA §5.4.

### 5.1 Usuário

| Propriedade | Origem | Onde fica |
|---|---|---|
| Nome completo, username, email, descrição | U | RDS, `users` |
| Senha | U | RDS, `users.hashed_password` (hash Argon2id; nunca em texto puro) |
| Imagem do perfil | U | S3 `users/{uid}/profile/`; chave em `users.profile_image_key` |
| Data de criação | S | RDS, `users.created_at` |
| Espaço usado | S | RDS, `users.storage_used_bytes` |

### 5.2 Imagem

| Propriedade | Origem | Onde fica |
|---|---|---|
| Nome do arquivo (nome exibido e nome original) | U / S | `media_objects.name` (editável) e `original_filename` |
| Tamanho em bytes, data de upload, tipo MIME | S | `media_objects` |
| Dimensões (largura × altura em px) | S | `image_metadata` |
| Profundidade de cor (bits por pixel) | S | `image_metadata` |
| Resolução (DPI), quando o arquivo informa | S | `image_metadata` |
| Dados EXIF, se houver: modelo da câmera, exposição, data/hora da captura, GPS | S | `image_metadata` (campos principais + EXIF completo em JSON) |
| Miniatura | S | S3 `users/{uid}/images/{id}/thumb.*`; chave em `media_objects.thumbnail_key` |
| Descrição, tags | U | `media_objects.description`, `tags` + `media_tags` |
| Arquivo original | U | S3 `users/{uid}/images/{id}/original.{ext}` |

### 5.3 Vídeo

| Propriedade | Origem | Onde fica |
|---|---|---|
| Nome, tamanho, data de upload, tipo MIME | U / S | `media_objects` |
| Duração, resolução, taxa de quadros, codec de vídeo, codec de áudio, taxa de bits | S | `video_metadata` (lidas com ffprobe) |
| Localização da miniatura | S | S3 `users/{uid}/videos/{id}/thumb.jpg`; `media_objects.thumbnail_key` |
| Detalhes do processamento: versões geradas e localizações | S | `media_variants` (rótulo, largura, altura, tamanho, chave, se é o original) e S3 `users/{uid}/videos/{id}/{1080p,720p,480p}.mp4` |
| Status do processamento e erro | S | `media_objects.status`, `error_code` |
| Descrição, tags, gênero | U | `media_objects`, `tags` + `media_tags` |

### 5.4 Áudio

| Propriedade | Origem | Onde fica |
|---|---|---|
| Nome, tamanho, data de upload, tipo MIME | U / S | `media_objects` |
| Duração, taxa de bits, taxa de amostragem, canais | S | `audio_metadata` (lidas com ffprobe) |
| Descrição, tags, gênero musical | U | `media_objects`, `tags` + `media_tags` |
| Arquivo original | U | S3 `users/{uid}/audios/{id}/original.{ext}` |

## 6. Formatos suportados

| Tipo | Formatos | Observações |
|---|---|---|
| Imagens | JPEG (JPG), PNG, GIF, SVG, WebP | SVG não tem EXIF nem DPI; a miniatura do SVG é o próprio arquivo (RN-09) |
| Áudios | MP3, WAV, OGG, FLAC | Toca o original. OGG tem suporte limitado no Safari (limitação conhecida) |
| Vídeos | MP4, AVI, MOV, WebM | AVI e vídeos com codec que o navegador não toca são convertidos para MP4 H.264/AAC (RN-04) |

O tipo é identificado pelo conteúdo do arquivo (RN-06), não pela extensão. Novos formatos podem ser acrescentados sem mudar o modelo de dados.

## 7. Regras de negócio

| ID | Regra |
|---|---|
| RN-01 | **Cota:** cada usuário tem 100 MB (104 857 600 bytes) de originais. Miniaturas e versões geradas não contam. O espaço é reservado ao iniciar o upload (operação atômica no banco), ajustado ao tamanho real ao concluir e devolvido na exclusão ou quando o upload é abandonado. Ex.: com 99 MB usados, um arquivo de 2 MB é recusado com 413 `QUOTA_EXCEEDED` e a mensagem mostra o espaço livre |
| RN-02 | **Tamanho máximo:** um arquivo tem no máximo 100 MB e nunca mais que o espaço livre do usuário. O limite é imposto pelo próprio S3 (condição `content-length-range` do POST pré-assinado), além da validação no cliente |
| RN-03 | **Isolamento por usuário:** toda consulta filtra pelo dono. Objeto de outro usuário responde **404** (não 403) em detalhe, edição e exclusão, e nunca aparece em listagem ou pesquisa. URLs pré-assinadas só são geradas para o dono |
| RN-04 | **Versões de vídeo:** (a) sem ampliação: só são geradas versões com altura menor ou igual à do original; (b) se o original já toca no navegador (MP4/WebM/MOV com H.264, VP8/VP9 ou AV1) e tem lado menor ≤ 1080, ele mesmo é a versão de topo; senão o worker gera um MP4 H.264/AAC na resolução nativa (limitada a 1080p); (c) 720p e 480p são geradas quando estão abaixo do original; (d) o padrão de reprodução é a maior versão ≤ 1080p; (e) vídeos com mais de 10 minutos são recusados no processamento (`failed`, `VIDEO_TOO_LONG`) |
| RN-05 | **Tags:** até 10 por arquivo, com até 40 caracteres cada; salvas em minúsculas, sem repetição; cada usuário tem as próprias tags |
| RN-06 | **Tipo pelo conteúdo:** o tipo é detectado pelos primeiros bytes do arquivo (assinatura) e, no caso do SVG, pela estrutura XML; extensão e `Content-Type` informados pelo navegador não bastam. Arquivo não reconhecido → 422 `UNSUPPORTED_FILE` e o objeto é removido |
| RN-07 | **Campos editáveis:** nome ≤ 255 caracteres (obrigatório), descrição ≤ 2000, gênero ≤ 50 (só áudio e vídeo) |
| RN-08 | **Processamento e falhas:** imagens são processadas na conclusão do upload; áudios e vídeos vão para a fila e ficam `queued`/`processing` até o worker terminar. Uma mensagem que falha 3 vezes vai para a DLQ e o objeto fica `failed` com o código do erro; arquivo corrompido fica `failed` (`INVALID_MEDIA`) sem novas tentativas |
| RN-09 | **Miniaturas:** imagens raster geram uma miniatura reduzida (lado maior de até 320 px, sem os dados EXIF); SVG usa o próprio arquivo como miniatura; vídeos usam o 1º quadro; áudios não têm miniatura (a interface mostra um ícone) |
| RN-10 | **Exclusão:** apaga o registro, o original, a miniatura e as versões, e devolve a cota |
| RN-11 | **Uploads abandonados:** upload iniciado e não concluído em 60 minutos é descartado (objeto apagado, se existir, e cota devolvida) |
| RN-12 | **Pesquisa:** sem diferença entre maiúsculas e minúsculas nem acentos; procura no nome, na descrição e nas tags; pode ser combinada com o filtro de tipo; resultados paginados, até 50 por página |

## 8. Requisitos não funcionais (mensuráveis)

A ERS pede tempos de resposta "a definir com o cliente". A equipe propõe os valores abaixo, verificados na issue de testes (#89) e no teste de carga (#88).

| ID | Categoria | Requisito | Como verificar | Issues |
|---|---|---|---|---|
| RNF-01 | Desempenho | p95 de `GET /api/files` (50 itens) < 1 s com 20 usuários simultâneos | Locust contra a produção; relatório com p95 | #70, #88 |
| RNF-02 | Desempenho | p95 de `POST /api/files/uploads` < 300 ms | Locust contra a produção | #69, #88 |
| RNF-03 | Desempenho | Imagem com miniatura pronta na resposta do `complete` (< 5 s para imagem de até 10 MB) | Teste de integração (status `ready` na resposta) + medição manual em produção | #68, #69, #89 |
| RNF-04 | Desempenho | Vídeo de 1 min em 1080p com versões prontas em < 3 min com worker ligado | Medição manual em produção (horário do upload × `ready`) | #73, #86, #89 |
| RNF-05 | Escalabilidade | Com CPU ou RAM > 80% por 3 min, o ASG do app lança uma instância; a nova instância fica InService em < 5 min | Carga com Locust e/ou `stress-ng`; prints do CloudWatch e do histórico de atividades do ASG | #85, #88 |
| RNF-06 | Escalabilidade | Com mensagens na fila, o ASG de workers sai de 0 para 1 em < 5 min e volta a 0 após 10 min de fila vazia | Enviar vídeos com o ASG em 0; prints dos alarmes e do histórico do ASG | #86, #88 |
| RNF-07 | Segurança | 0 acessos a objetos de outro usuário nos testes (API → 404; S3 direto → `AccessDenied`) | Testes automatizados de acesso cruzado + teste manual da URL direta do S3 | #70, #89 |
| RNF-08 | Segurança | Bucket sem acesso público; URLs pré-assinadas de no máximo 1 h; HTTPS obrigatório | Configuração do bucket no report; teste de URL expirada; HTTP redireciona para HTTPS na CloudFront | #67, #79, #84, #89 |
| RNF-09 | Usabilidade | Interface responsiva (360 px a 1440 px), com estados de carregando, erro e vazio em toda tela | Checklist manual em larguras de celular e desktop; testes de componente dos estados | #66, #75, #76, #77, #78, #89 |
| RNF-10 | Capacidade | Cota de 100 MB por usuário (99 MB usados + arquivo de 2 MB → recusado com mensagem clara) | Teste automatizado do service + teste manual em produção | #69, #76, #89 |

## 9. Interpretações e decisões

### 9.1 "Atualizar conteúdo" (RF-2.4)

O RF-2.4 cita "editar informações e conteúdo" e dá como exemplos renomear, atualizar a descrição e adicionar tags. A equipe interpreta "conteúdo" como esses **metadados editáveis** (nome, descrição, tags, gênero). Trocar o arquivo em si é feito excluindo o objeto e enviando de novo, o que mantém a cota e as versões geradas coerentes (ADR-029).

### 9.2 "Reprodução" de vídeo e áudio

Reproduzir significa o navegador buscar o arquivo por uma URL pré-assinada e tocá-lo no `<video>`/`<audio>`, com download progressivo (pode começar a tocar antes de baixar tudo). Não há streaming adaptativo (HLS/DASH). Por isso todas as versões geradas são MP4 com o índice no início (`+faststart`).

### 9.3 "Resolução padrão de 1080p" (RF-2.11)

A ERS supõe vídeos enviados em 1080p. Para vídeos menores, a equipe não amplia a imagem (ampliar só aumenta o arquivo, sem ganho de qualidade): o padrão é a maior versão disponível até 1080p (RN-04, ADR-023).

### 9.4 "Listar todos os objetos no sistema" (RF-4.1)

Por causa do requisito de segurança da ERS ("cada usuário só tem acesso a seus próprios objetos"), "todos os objetos" significa todos os objetos **do usuário logado** (RN-03, ADR-029).

### 9.5 Cota de armazenamento

A ERS não fala de cota. A equipe adotou 100 MB por usuário para controlar os custos da conta AWS do projeto e para permitir testar o limite com arquivos pequenos (RN-01, ADR-022).

## 10. Fora do escopo

- Compartilhar objetos entre usuários, pastas e lixeira.
- Streaming adaptativo (HLS/DASH) e legendas.
- Editar o conteúdo da mídia (recortar, girar, cortar trechos) ou trocar o arquivo de um objeto existente.
- Converter áudios para outros formatos.
- Uploads acima de 100 MB, upload retomável e envio de pastas.
- Papéis de administrador, recuperação de senha por email, aplicativo móvel.
- Remover dados EXIF/GPS do original enviado (a miniatura já sai sem EXIF; o GPS só é mostrado ao dono).

## 11. Matriz de rastreabilidade

Tipos de teste: **U** = unitário, **I** = integração (API com banco de teste), **C** = componente do frontend, **M** = manual em produção (checklist da #89), **L** = carga (Locust, #88).

| Requisito | Issues | Teste |
|---|---|---|
| RF-1.1 | Sprint 1 (#8, #13) | I, C (sprint 1); M (regressão em produção, #89) |
| RF-1.2 | Sprint 1 (#7, #9); #84 | I (sprint 1); M (login, cookie e CSRF pela CloudFront) |
| RF-1.3 | Sprint 1 (#10, #11, #15, #16); #67, #79 | I (avatar em `users/{uid}/profile/`); M |
| RF-2.1 | #66, #67, #69, #76, #79 | U, I (iniciar/concluir upload), C (painel de envio), M |
| RF-2.2 | #67, #79, #81 | U (storage com moto), M (URL direta → `AccessDenied`) |
| RF-2.3 | #70, #77 | I (detalhe), C (página de visualização) |
| RF-2.4 | #70, #77 | I (PATCH), C (formulário de edição) |
| RF-2.5 | #70, #77 | I (DELETE apaga objetos e devolve a cota), C, M |
| RF-2.6 | #68, #69 | U (miniatura e propriedades), I (`complete` → `ready`) |
| RF-2.7 | #70, #75 | I (listagem traz URL da miniatura), C (grade) |
| RF-2.8 | #72, #73 | U (ffmpeg com vídeo gerado no teste) |
| RF-2.9 | #75, #78 | C (grade e pôster do player) |
| RF-2.10 | #72, #73, #86 | U (regras de versões sem ampliação), M (vídeo real em produção) |
| RF-2.11 | #70, #78 | I (detalhe lista as versões e a padrão), C (troca de qualidade), M |
| RF-2.12 | #72, #74 | U (ffprobe com áudio gerado no teste), M |
| RF-3.1 | #70, #75 | I (pesquisa por nome, descrição, tag, sem acento) |
| RF-3.2 | #75 | C (resultados e estado vazio) |
| RF-4.1 | #70, #75 | I (paginação), C |
| RF-4.2 | #66, #70, #75 | I (filtro por tipo), C (barra lateral) |
| RF-4.3 | #70, #75 | I (tipo + pesquisa), C |
| RF-5.1 | #75, #77 | C (navegação para o detalhe) |
| RF-5.2 | #77, #78 | C (prévia por tipo), M |
| RNF-01, RNF-02 | #69, #70, #88 | L |
| RNF-03 | #68, #69, #89 | I, M |
| RNF-04 | #73, #86, #89 | M |
| RNF-05 | #85, #88 | L, M (CloudWatch e ASG) |
| RNF-06 | #86, #88 | M (alarmes e ASG) |
| RNF-07 | #70, #89 | I (acesso cruzado), M |
| RNF-08 | #67, #79, #84, #89 | U, M |
| RNF-09 | #66, #75–#78, #89 | C, M |
| RNF-10 | #69, #76, #89 | U, I, M |
