# Relatório de validação — Análise de documentos financeiros

Este relatório converte os cenários de [quickstart.md](./quickstart.md) em um roteiro executável e registrável. Use-o para validar a aplicação em ambiente local; os resultados abaixo começam como **Pendente** e devem ser preenchidos durante a execução.

## 1. Identificação da execução

| Campo | Preencher |
|---|---|
| Data e hora | |
| Responsável | |
| Branch/commit validado | |
| Ambiente (Windows, versões de Python/Node/Docker) | |
| URL da aplicação | |
| Resultado geral | Pendente / Aprovado / Reprovado / Bloqueado |

**Critério geral:** marque um cenário como aprovado somente quando todos os resultados esperados forem observados e houver evidência registrada. Falha inesperada é **Reprovado**; falta de chave, serviço ou dado de teste é **Bloqueado**, não aprovado.

## 2. Preparação

1. Siga [quickstart.md](./quickstart.md) até iniciar PostgreSQL/pgvector, MinIO, API e frontend.
2. Confirme `http://127.0.0.1:8000/health` (`{"status":"ok"}`) e abra o endereço Vite, normalmente `http://127.0.0.1:5173`.
3. Para cenários com perguntas ou análise, configure uma chave válida para o provedor selecionado por `AI_PROVIDER` (`OPENAI_API_KEY` ou `GOOGLE_API_KEY`) no `backend\.env`. Não a inclua neste relatório nem em evidências.
4. Use somente PDFs sintéticos/de teste. O modo demo usa identidades fixas e compartilhadas; não use documentos reais, confidenciais ou decisões financeiras reais.
5. Para validar aprovações, entre uma vez como **Guest approver**, saia e entre como **Guest analyst** antes de enviar o relatório, conforme o quickstart. Isso prepara a identidade do aprovador designado no fluxo demo.
6. Use o PDF sintético de teste [financial-report-validation-sample.pdf](./samples/financial-report-validation-sample.pdf), com três páginas numeradas e dados fictícios;
7. Para o cenário VAL-03, use estas perguntas:
   - **Com evidência:** “Qual foi a receita líquida em 2025?” Resposta que deve ser verificável: **R$ 12.500 mil (R$ 12,5 milhões)**, na página 1.
   - **Sem evidência:** “Qual é a previsão de receita líquida para 2026?” O documento informa que não contém essa previsão; a resposta esperada é que não há evidência suficiente, sem estimar ou inventar um valor.
8. Tenha também um arquivo inválido para o teste VAL-06 (por exemplo, um `.txt` ou PDF vazio/corrompido).

**Pré-verificações**

| Verificação | Resultado/evidência |
|---|---|
| Containers PostgreSQL/pgvector e MinIO ativos (`docker ps`) | |
| Bucket `financial-reports` criado no MinIO | |
| Migrações aplicadas sem erro | |
| API saudável e frontend acessível | |
| Chave do provedor de IA selecionado disponível (não registrar o valor) | |
| Login como Guest approver e depois como Guest analyst concluído | |

## 3. Cenários manuais

### VAL-01 — Enviar relatório e acompanhar o processamento

**Passos**
1. Como Guest analyst, envie [financial-report-validation-sample.pdf](./samples/financial-report-validation-sample.pdf) pela área de relatórios.
2. Anote o nome/identificador exibido e observe o estado até o processamento terminar.
3. Atualize a página e localize o relatório novamente.

**Resultado esperado**
- O envio é confirmado e o relatório permanece disponível após atualizar a página.
- O estado mostra o progresso (na fila/em processamento) e termina como concluído, ou apresenta uma falha clara.
- Um relatório com falha não é apresentado como análise concluída.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Evidência (ID, estados, captura/log):**

### VAL-02 — Conferir achados e citações

**Passos**
1. Abra a análise concluída do VAL-01.
2. Escolha pelo menos três achados com referências, incluindo páginas diferentes quando disponíveis.
3. Abra cada referência e compare o trecho/página exibido com o PDF original.

**Resultado esperado**
- As referências levam à página ou trecho correspondente e permitem verificar a afirmação.
- A interface não apresenta uma referência quebrada como evidência válida.
- Quando a autorização à fonte não existe ou foi revogada, a fonte não revela seu conteúdo. O modo demo usa identidades compartilhadas, portanto essa verificação de isolamento deve ser feita também com usuários de teste distintos ou pela validação de API apropriada.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Achados conferidos e evidência:**

### VAL-03 — Pergunta com evidência, sem evidência e persistência do histórico

**Passos**
1. Na tela do relatório, pergunte: “Qual foi a receita líquida em 2025?”
2. Confira resposta e citações; abra as citações e verifique o conteúdo.
3. Faça a pergunta: “Qual é a previsão de receita líquida para 2026?” O PDF não fornece essa previsão.
4. Atualize a página ou reabra o relatório e confira o histórico das duas perguntas.

**Resultado esperado**
- A resposta apoiada em evidência é concisa e aponta para fontes verificáveis.
- A pergunta sem suporte é identificada claramente como insuficiência de evidência; não é apresentada como fato.
- O histórico e as limitações permanecem visíveis após reabrir o relatório.
- Se a fonte está fora do escopo de acesso, sua informação não aparece na resposta nem nas citações.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Perguntas usadas, evidências e limitações:**

### VAL-04 — Recomendação sensível pendente e recuperação após reinício

**Passos**
1. Envie um relatório de teste que, conforme os critérios de sensibilidade configurados, gere uma recomendação sujeita à aprovação humana.
2. Confira se a recomendação está pendente e aparece na fila do Guest approver designado.
3. Sem decidir, reinicie somente a API (Ctrl+C no Uvicorn; inicie-a novamente conforme o quickstart) e reabra as telas.

**Resultado esperado**
- A recomendação sensível é identificada como pendente, encaminhada ao aprovador e não aparece como aprovada.
- A recomendação continua pendente e na fila após o reinício da API.

**Importante:** a geração por modelo pode não ser determinística. Se o relatório não gerar uma recomendação sensível, registre **Bloqueado** e repita com dados de teste adequados ou com uma recomendação preparada no ambiente de teste; não registre aprovação apenas porque a tela abriu.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**ID da recomendação, estado antes/depois e evidência:**

### VAL-05 — Negar usuário não autorizado e registrar decisão autorizada

**Passos**
1. Com uma recomendação pendente, tente decidir como Guest analyst, usando a interface ou a API `POST /api/v1/recommendations/{recommendation_id}/decision` em `http://127.0.0.1:8000/docs`.
2. Confira a resposta de negação e, em seguida, a trilha de auditoria/estado da recomendação.
3. Entre como o Guest approver designado e aprove ou rejeite a recomendação, fornecendo um motivo quando solicitado.
4. Reabra a recomendação e confira estado e histórico da decisão.

**Resultado esperado**
- O analista não consegue aprovar/rejeitar: a API nega a operação e a tentativa é auditada.
- A tentativa negada não altera a recomendação pendente.
- O aprovador designado consegue registrar aprovação ou rejeição; o estado final e o autor da decisão ficam visíveis no histórico.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Identidade/ação, resposta, estado e evidência (não incluir tokens):**

### VAL-06 — Entrada inválida e indisponibilidade de serviço

**Passos**
1. Tente enviar um arquivo que não seja PDF e, separadamente, um PDF vazio, corrompido ou ilegível.
2. Confirme como a interface representa a rejeição/falha; não use o arquivo inválido como relatório concluído.
3. Em uma execução controlada, pare o container MinIO (`docker stop financial-minio`) e tente um envio de teste. Registre o comportamento.
4. Reinicie MinIO (`docker start financial-minio`) e confirme a recuperação. Não pare o banco durante uma execução com dados que queira preservar.

**Resultado esperado**
- Arquivos não suportados, vazios ou ilegíveis produzem erro compreensível e não uma análise completa.
- Se armazenamento/serviço de conhecimento estiver indisponível, a falha ou limitação é explícita; o sistema não sugere que o trabalho parcial foi concluído.
- Após restabelecer MinIO, um novo teste pode ser executado normalmente.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Arquivo/serviço testado, mensagem e evidência:**

### VAL-07 — Jornada de revisão em desktop e mobile

**Passos**
1. No navegador, valide a jornada do analista em viewport desktop (por exemplo, 1366 × 768).
2. Repita em viewport mobile (por exemplo, 390 × 844).
3. Em ambos, localize o relatório, abra um achado e sua fonte, consulte uma pergunta/resposta e localize o estado/ação de aprovação.

**Resultado esperado**
- Conteúdo, fontes, estados e ações essenciais continuam legíveis e utilizáveis nas duas larguras.
- Não há conteúdo ou ação essencial cortada, sobreposta ou inacessível por rolagem/teclado.

**Resultado:** Pendente / Aprovado / Reprovado / Bloqueado  
**Navegadores/viewports e evidências:**

## 4. Verificações automatizadas

Execute a partir das pastas indicadas. Registre o comando, data, resultado e resumo da saída; não copie segredos para logs compartilhados.

| Verificação | Comando | Resultado |
|---|---|---|
| Lint do backend (`backend\`) | `.\.venv\Scripts\python.exe -m ruff check .` | Pendente |
| Testes do backend (`backend\`) | `.\.venv\Scripts\python.exe -m pytest` | Pendente |
| Build/type-check do frontend (`frontend\`) | `npm run build` | Pendente |
| Testes do frontend (`frontend\`) | `npm test` | Pendente |

Os testes de integração dependem de PostgreSQL/pgvector e armazenamento S3 compatível. Os testes unitários não devem precisar de credenciais de produção.

### Cobertura já identificada no repositório

- Upload, validação de PDF e transições de estado: `backend/tests/unit/test_upload_and_state.py`.
- Pergunta sem evidência e persistência da resposta: `backend/tests/api/test_questions.py`.
- Negação/auditoria e decisão por aprovador designado: `backend/tests/api/test_approvals.py`.
- Entrada e login demo: `backend/tests/api/test_demo_auth.py` e `frontend/tests/workspace.test.tsx`.
- Testes e2e de integração e de layout mobile estão listados como pendentes em `specs/001-financial-document-analysis/tasks.md` (T022, T027, T030, T032). Assim, sucesso nos testes existentes não substitui os cenários manuais deste relatório.

## 5. Resumo e decisão

| ID | Cenário | Resultado | Evidência/observação |
|---|---|---|---|
| VAL-01 | Envio e processamento do relatório | Pendente | |
| VAL-02 | Achados e citações | Pendente | |
| VAL-03 | Perguntas, lacuna de evidência e histórico | Pendente | |
| VAL-04 | Aprovação pendente e persistência | Pendente | |
| VAL-05 | Autorização, auditoria e decisão | Pendente | |
| VAL-06 | Entrada inválida/serviço indisponível | Pendente | |
| VAL-07 | Usabilidade desktop/mobile | Pendente | |
| AUTO-01 | Lint e testes do backend | Pendente | |
| AUTO-02 | Build e testes do frontend | Pendente | |

**Decisão final:** Pendente / Aprovado / Reprovado  
**Bloqueios ou defeitos encontrados (referência, passos para reproduzir e impacto):**

**Aprovado por / data:**
