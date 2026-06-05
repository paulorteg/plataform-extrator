import { Component, useEffect, useMemo, useState } from "react";

import {
  getSupabaseSession,
  loadCurrentUser,
  signInWithSupabase,
  signOutFromSupabase,
} from "./lib/auth/session.js";
import { DocumentUploadRequestError, uploadDocument } from "./lib/api/documents.js";
import {
  fetchDocumentProcessingJobs,
  fetchProcessingJob,
  ProcessingJobRequestError,
} from "./lib/api/processing-jobs.js";
import { appRoutes, getCurrentRoute } from "./lib/routes.js";

const requiredPublicEnv = [
  {
    key: "VITE_API_BASE_URL",
    label: "API",
    value: import.meta.env.VITE_API_BASE_URL,
  },
  {
    key: "VITE_SUPABASE_URL",
    label: "Supabase URL",
    value: import.meta.env.VITE_SUPABASE_URL,
  },
  {
    key: "VITE_SUPABASE_ANON_KEY",
    label: "Supabase anon key",
    value: import.meta.env.VITE_SUPABASE_ANON_KEY,
  },
];

const routeContent = {
  dashboard: {
    title: "Visao geral",
    eyebrow: "Operacao",
    body: "Acompanhe o ciclo documental, pendencias de revisao e atividades recentes da organizacao ativa.",
  },
  documents: {
    title: "Documentos",
    eyebrow: "Entrada documental",
    body: "Centralize documentos recebidos, status de processamento e prioridade operacional.",
  },
  upload: {
    title: "Upload de BO",
    eyebrow: "Entrada documental",
    body: "Envie documentos sinteticos ou anonimizados para processamento pelo backend.",
  },
  processing: {
    title: "Status do processamento",
    eyebrow: "Acompanhamento",
    body: "Acompanhe o job documental com status sanitizado retornado pela API.",
  },
  occurrences: {
    title: "Ocorrencias",
    eyebrow: "Extracao",
    body: "Acompanhe ocorrencias estruturadas, pendencias de validacao e progresso de revisao.",
  },
  review: {
    title: "Revisao",
    eyebrow: "Controle humano",
    body: "Priorize itens pendentes, verifique evidencias e acompanhe aprovacoes.",
  },
};

const uploadRules = {
  maxBytes: 25 * 1024 * 1024,
  allowedTypes: ["application/pdf", "image/jpeg", "image/png", "image/tiff"],
  allowedExtensions: [".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"],
};

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "0 MB";
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateUploadFile(file) {
  if (!file) {
    return "Selecione um arquivo para enviar.";
  }
  if (file.size <= 0) {
    return "O arquivo selecionado esta vazio.";
  }
  if (file.size > uploadRules.maxBytes) {
    return `O arquivo deve ter ate ${formatBytes(uploadRules.maxBytes)}.`;
  }
  if (!uploadRules.allowedTypes.includes(file.type)) {
    return "Formato nao suportado. Use PDF, JPEG, PNG ou TIFF.";
  }
  return null;
}

function friendlyUploadError(error) {
  if (error instanceof DocumentUploadRequestError) {
    if (error.status === 401) return "Sessao expirada. Entre novamente antes de enviar.";
    if (error.status === 403) return "Sua organizacao ativa nao permite este envio.";
    if (error.status === 413) return "O arquivo excede o limite permitido.";
    if (error.status === 400) return "O arquivo selecionado nao atende aos requisitos de upload.";
    if (error.status === 502) return "Storage indisponivel no momento. Tente novamente mais tarde.";
  }

  if (error?.message === "Missing active organization.") {
    return "Selecione uma organizacao ativa para enviar o documento.";
  }

  return "Nao foi possivel enviar o documento agora.";
}

function friendlyProcessingError(error) {
  if (error instanceof ProcessingJobRequestError) {
    if (error.status === 401) return "Sessao expirada. Entre novamente antes de consultar.";
    if (error.status === 403) return "Sua organizacao ativa nao permite consultar este job.";
    if (error.status === 404) return "Job ou documento nao encontrado para esta organizacao.";
  }

  if (error?.message === "Missing active organization.") {
    return "Selecione uma organizacao ativa para consultar o status.";
  }

  return "Nao foi possivel consultar o status do processamento agora.";
}

function statusLabel(status) {
  const labels = {
    pending: "Pendente",
    queued: "Pendente",
    running: "Em execucao",
    processing: "Em execucao",
    completed: "Concluido",
    failed: "Falha",
  };

  return labels[status] ?? status ?? "Desconhecido";
}

function statusClass(status) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running" || status === "processing") return "progress";
  return "pending";
}

function formatDateTime(value) {
  if (!value) return "Nao informado";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Nao informado";
  }

  return date.toLocaleString("pt-BR");
}

function getProcessingQuery() {
  if (typeof window === "undefined") {
    return { jobId: "", documentId: "" };
  }

  const queryText = window.location.hash.split("?")[1] ?? "";
  const params = new URLSearchParams(queryText);
  return {
    jobId: params.get("job_id") ?? "",
    documentId: params.get("document_id") ?? "",
  };
}

function useRoute() {
  const [route, setRoute] = useState(() => getCurrentRoute());

  useEffect(() => {
    const onHashChange = () => setRoute(getCurrentRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return route;
}

function useSessionGate(isConfigured) {
  const [state, setState] = useState({
    status: isConfigured ? "loading" : "configuration_missing",
    user: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;

    async function loadSession() {
      if (!isConfigured) {
        setState({
          status: "configuration_missing",
          user: null,
          error: null,
        });
        return;
      }

      setState({ status: "loading", user: null, error: null });

      try {
        const user = await loadCurrentUser();
        if (!isMounted) return;

        setState({
          status: user ? "authenticated" : "unauthenticated",
          user,
          error: null,
        });
      } catch (error) {
        if (!isMounted) return;

        setState({
          status: "error",
          user: null,
          error,
        });
      }
    }

    loadSession();

    return () => {
      isMounted = false;
    };
  }, [isConfigured]);

  async function signIn(email, password) {
    if (!isConfigured) {
      setState({
        status: "configuration_missing",
        user: null,
        error: null,
      });
      return;
    }

    setState({ status: "signing_in", user: null, error: null });

    const { error } = await signInWithSupabase(email, password);
    if (error) {
      setState({
        status: "unauthenticated",
        user: null,
        error: new Error("Credenciais invalidas ou sessao nao autorizada."),
      });
      return;
    }

    try {
      const user = await loadCurrentUser();
      setState({
        status: user ? "authenticated" : "unauthenticated",
        user,
        error: user
          ? null
          : new Error("Sessao criada, mas usuario interno nao encontrado."),
      });
    } catch {
      setState({
        status: "unauthenticated",
        user: null,
        error: new Error("Sessao criada, mas o perfil interno nao carregou."),
      });
    }
  }

  async function signOut() {
    setState((current) => ({
      ...current,
      status: "signing_out",
      error: null,
    }));

    await signOutFromSupabase();

    setState({
      status: "unauthenticated",
      user: null,
      error: null,
    });
  }

  return { ...state, signIn, signOut };
}

export function App() {
  return (
    <AppErrorBoundary>
      <AppContent />
    </AppErrorBoundary>
  );
}

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return <SessionError error={this.state.error} />;
    }

    return this.props.children;
  }
}

function AppContent() {
  const configuredCount = requiredPublicEnv.filter((item) => item.value).length;
  const isConfigured = configuredCount === requiredPublicEnv.length;
  const sessionGate = useSessionGate(isConfigured);
  const route = useRoute();
  const content = routeContent[route.id] ?? routeContent.dashboard;
  const organizations = sessionGate.user?.organizations ?? [];
  const currentUser = sessionGate.user?.user ?? sessionGate.user;
  const displayName = useMemo(
    () => currentUser?.name ?? currentUser?.email ?? "Usuario",
    [currentUser],
  );

  if (sessionGate.status === "configuration_missing") {
    return <ConfigurationMissing />;
  }

  if (sessionGate.status === "loading") {
    return <LoadingShell />;
  }

  if (
    sessionGate.status === "unauthenticated" ||
    sessionGate.status === "signing_in"
  ) {
    return (
      <LoginShell
        error={sessionGate.error}
        isSubmitting={sessionGate.status === "signing_in"}
        onSubmit={sessionGate.signIn}
      />
    );
  }

  if (sessionGate.status === "error") {
    return <SessionError error={sessionGate.error} />;
  }

  return (
    <main className="app-shell" data-authenticated="true">
      <aside className="sidebar" aria-label="Navegacao principal">
        <div className="brand">
          <span className="brand-mark">M</span>
          <span>
            <strong>MercadoIA</strong>
            <small>BO Platform</small>
          </span>
        </div>
        <nav className="nav-list">
          {appRoutes.map((item) => (
            <a
              aria-current={route.id === item.id ? "page" : undefined}
              href={item.path}
              key={item.id}
            >
              <strong>{item.label}</strong>
              <small>{item.description}</small>
            </a>
          ))}
        </nav>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">{content.eyebrow}</span>
            <h1>{content.title}</h1>
          </div>
          <div className="user-badge" aria-label="Usuario autenticado">
            <span>{displayName.slice(0, 1).toUpperCase()}</span>
            <strong>{displayName}</strong>
          </div>
          <button
            className="ghost-button"
            disabled={sessionGate.status === "signing_out"}
            onClick={sessionGate.signOut}
            type="button"
          >
            {sessionGate.status === "signing_out" ? "Saindo" : "Sair"}
          </button>
        </header>

        {route.id === "upload" ? (
          <UploadWorkspace organizations={organizations} />
        ) : route.id === "processing" ? (
          <ProcessingWorkspace organizations={organizations} />
        ) : (
          <section className="content-grid">
            <article className="workspace-card primary">
              <span className="section-label">{route.label}</span>
              <h2>{content.title}</h2>
              <p>{content.body}</p>
              <div className="status-row">
                <span className="status ready">Sessao ativa</span>
                <span className="meta">Rotas futuras preparadas</span>
              </div>
            </article>

            <article className="workspace-card">
              <span className="section-label">Fila operacional</span>
              <h2>Prioridades</h2>
              <ul className="plain-list">
                <li>Documentos aguardando triagem</li>
                <li>Ocorrencias com campos pendentes</li>
                <li>Templates aguardando aprovacao</li>
              </ul>
            </article>
          </section>
        )}
      </section>
    </main>
  );
}

function UploadWorkspace({ organizations }) {
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(
    () => organizations[0]?.id ?? "",
  );
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadState, setUploadState] = useState({
    status: "idle",
    error: null,
    result: null,
  });

  useEffect(() => {
    if (!selectedOrganizationId && organizations[0]?.id) {
      setSelectedOrganizationId(organizations[0].id);
    }
  }, [organizations, selectedOrganizationId]);

  const fileValidationMessage = selectedFile ? validateUploadFile(selectedFile) : null;
  const canUpload =
    Boolean(selectedOrganizationId) &&
    Boolean(selectedFile) &&
    !fileValidationMessage &&
    uploadState.status !== "uploading";

  function handleFileChange(event) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadState({ status: "idle", error: null, result: null });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const validationMessage = validateUploadFile(selectedFile);
    if (validationMessage) {
      setUploadState({ status: "error", error: validationMessage, result: null });
      return;
    }

    setUploadState({ status: "uploading", error: null, result: null });

    try {
      const session = await getSupabaseSession();
      const accessToken = session?.access_token;
      const result = await uploadDocument({
        file: selectedFile,
        accessToken,
        organizationId: selectedOrganizationId,
      });
      setUploadState({ status: "success", error: null, result });
    } catch (error) {
      setUploadState({
        status: "error",
        error: friendlyUploadError(error),
        result: null,
      });
    }
  }

  return (
    <section className="upload-layout">
      <form className="workspace-card upload-card" onSubmit={handleSubmit}>
        <span className="section-label">Upload seguro</span>
        <h2>Enviar BO ou documento</h2>
        <p>
          O arquivo e enviado para a API e processado no backend. O frontend nao le
          o conteudo textual do documento.
        </p>

        <label className="field-block">
          Organizacao ativa
          <select
            disabled={uploadState.status === "uploading" || organizations.length === 0}
            onChange={(event) => setSelectedOrganizationId(event.target.value)}
            required
            value={selectedOrganizationId}
          >
            {organizations.length === 0 ? (
              <option value="">Nenhuma organizacao disponivel</option>
            ) : null}
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
        </label>

        <label className="file-picker">
          <input
            accept={uploadRules.allowedExtensions.join(",")}
            disabled={uploadState.status === "uploading"}
            onChange={handleFileChange}
            required
            type="file"
          />
          <span>
            <strong>{selectedFile ? selectedFile.name : "Selecionar arquivo"}</strong>
            <small>
              PDF, JPEG, PNG ou TIFF ate {formatBytes(uploadRules.maxBytes)}
            </small>
          </span>
        </label>

        {selectedFile ? (
          <div className="file-summary" aria-live="polite">
            <span>{selectedFile.type || "tipo nao informado"}</span>
            <span>{formatBytes(selectedFile.size)}</span>
          </div>
        ) : null}

        {fileValidationMessage ? (
          <p className="form-error" role="alert">
            {fileValidationMessage}
          </p>
        ) : null}

        {uploadState.error ? (
          <p className="form-error" role="alert">
            {uploadState.error}
          </p>
        ) : null}

        <button className="primary-button" disabled={!canUpload} type="submit">
          {uploadState.status === "uploading" ? "Enviando" : "Enviar documento"}
        </button>
      </form>

      <article className="workspace-card upload-card secondary">
        <span className="section-label">Resultado</span>
        {uploadState.status === "success" && uploadState.result ? (
          <UploadSuccess result={uploadState.result} />
        ) : (
          <>
            <h2>Aguardando envio</h2>
            <p>
              Apos o upload, a API cria o documento e um job de processamento.
              O acompanhamento sera feito na proxima tela do fluxo.
            </p>
            <ul className="plain-list">
              <li>Sem leitura de conteudo no frontend</li>
              <li>Sem upload direto para Supabase Storage</li>
              <li>Headers de autenticacao e organizacao enviados para a API</li>
            </ul>
          </>
        )}
      </article>
    </section>
  );
}

function UploadSuccess({ result }) {
  const processingHref = `#/processing?job_id=${encodeURIComponent(
    result.job_id,
  )}&document_id=${encodeURIComponent(result.document_id)}`;

  return (
    <>
      <h2>Documento enviado</h2>
      <p>
        O documento foi registrado e o processamento foi enfileirado pelo backend.
      </p>
      <dl className="result-list">
        <div>
          <dt>Document ID</dt>
          <dd>{result.document_id}</dd>
        </div>
        <div>
          <dt>Job ID</dt>
          <dd>{result.job_id}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{result.status}</dd>
        </div>
      </dl>
      <a className="ghost-link" href={processingHref}>
        Acompanhar processamento
      </a>
    </>
  );
}

function ProcessingWorkspace({ organizations }) {
  const initialQuery = useMemo(() => getProcessingQuery(), []);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(
    () => organizations[0]?.id ?? "",
  );
  const [jobId, setJobId] = useState(initialQuery.jobId);
  const [documentId, setDocumentId] = useState(initialQuery.documentId);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [state, setState] = useState({
    status: "idle",
    error: null,
    jobs: [],
    lastUpdatedAt: null,
  });

  useEffect(() => {
    if (!selectedOrganizationId && organizations[0]?.id) {
      setSelectedOrganizationId(organizations[0].id);
    }
  }, [organizations, selectedOrganizationId]);

  async function loadStatus({ silent = false } = {}) {
    const trimmedJobId = jobId.trim();
    const trimmedDocumentId = documentId.trim();
    if (!trimmedJobId && !trimmedDocumentId) {
      setState({
        status: "error",
        error: "Informe um Job ID ou Document ID para consultar.",
        jobs: [],
        lastUpdatedAt: null,
      });
      return;
    }

    setState((current) => ({
      ...current,
      status: silent ? current.status : "loading",
      error: null,
    }));

    try {
      const session = await getSupabaseSession();
      const accessToken = session?.access_token;
      const request = {
        accessToken,
        organizationId: selectedOrganizationId,
      };
      const payload = trimmedJobId
        ? await fetchProcessingJob({ ...request, jobId: trimmedJobId })
        : await fetchDocumentProcessingJobs({ ...request, documentId: trimmedDocumentId });
      const jobs = trimmedJobId ? [payload] : payload.items ?? [];
      setState({
        status: "success",
        error: null,
        jobs,
        lastUpdatedAt: new Date().toLocaleTimeString("pt-BR"),
      });
    } catch (error) {
      setState({
        status: "error",
        error: friendlyProcessingError(error),
        jobs: [],
        lastUpdatedAt: null,
      });
    }
  }

  useEffect(() => {
    if (!autoRefresh) return undefined;

    const intervalId = window.setInterval(() => {
      loadStatus({ silent: true });
    }, 8000);

    return () => window.clearInterval(intervalId);
  }, [autoRefresh, documentId, jobId, selectedOrganizationId]);

  const canSearch =
    Boolean(selectedOrganizationId) &&
    Boolean(jobId.trim() || documentId.trim()) &&
    state.status !== "loading";

  return (
    <section className="processing-layout">
      <form
        className="workspace-card processing-card"
        onSubmit={(event) => {
          event.preventDefault();
          loadStatus();
        }}
      >
        <span className="section-label">Consulta segura</span>
        <h2>Acompanhar processamento</h2>
        <p>
          Consulte o status sanitizado retornado pela API. Metadata, conteudo do
          documento, OCR integral e erros internos nao sao exibidos.
        </p>

        <label className="field-block">
          Organizacao ativa
          <select
            disabled={state.status === "loading" || organizations.length === 0}
            onChange={(event) => setSelectedOrganizationId(event.target.value)}
            required
            value={selectedOrganizationId}
          >
            {organizations.length === 0 ? (
              <option value="">Nenhuma organizacao disponivel</option>
            ) : null}
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-block">
          Job ID
          <input
            autoComplete="off"
            onChange={(event) => setJobId(event.target.value)}
            placeholder="ID retornado no upload"
            value={jobId}
          />
        </label>

        <label className="field-block">
          Document ID
          <input
            autoComplete="off"
            onChange={(event) => setDocumentId(event.target.value)}
            placeholder="Opcional: listar jobs de um documento"
            value={documentId}
          />
        </label>

        <label className="toggle-row">
          <input
            checked={autoRefresh}
            onChange={(event) => setAutoRefresh(event.target.checked)}
            type="checkbox"
          />
          Atualizar automaticamente a cada 8 segundos
        </label>

        {state.error ? (
          <p className="form-error" role="alert">
            {state.error}
          </p>
        ) : null}

        <button className="primary-button" disabled={!canSearch} type="submit">
          {state.status === "loading" ? "Consultando" : "Atualizar status"}
        </button>
      </form>

      <article className="workspace-card processing-card secondary">
        <span className="section-label">Status</span>
        {state.jobs.length > 0 ? (
          <>
            <div className="status-row">
              <span className="meta">
                {state.lastUpdatedAt ? `Atualizado as ${state.lastUpdatedAt}` : "Atualizado"}
              </span>
            </div>
            <div className="job-list">
              {state.jobs.map((job) => (
                <ProcessingJobCard job={job} key={job.id} />
              ))}
            </div>
          </>
        ) : (
          <>
            <h2>Aguardando consulta</h2>
            <p>
              Informe um Job ID ou Document ID. Jobs concluidos liberam o caminho
              para consultar ocorrencias quando elas estiverem disponiveis.
            </p>
          </>
        )}
      </article>
    </section>
  );
}

function ProcessingJobCard({ job }) {
  const errorCode = job.error?.code ? `Codigo: ${job.error.code}` : null;
  const errorMessage = job.error?.message ?? "Falha controlada no processamento.";

  return (
    <section className="job-card">
      <div className="job-card-header">
        <span className={`status ${statusClass(job.status)}`}>{statusLabel(job.status)}</span>
        <strong>{job.job_type}</strong>
      </div>
      <dl className="result-list compact">
        <div>
          <dt>Job ID</dt>
          <dd>{job.id}</dd>
        </div>
        <div>
          <dt>Document ID</dt>
          <dd>{job.document_id}</dd>
        </div>
        <div>
          <dt>Tentativas</dt>
          <dd>
            {job.attempts} de {job.max_attempts}
          </dd>
        </div>
        <div>
          <dt>Criado em</dt>
          <dd>{formatDateTime(job.created_at)}</dd>
        </div>
        <div>
          <dt>Atualizado em</dt>
          <dd>{formatDateTime(job.updated_at)}</dd>
        </div>
        <div>
          <dt>Iniciado em</dt>
          <dd>{formatDateTime(job.started_at)}</dd>
        </div>
        <div>
          <dt>Finalizado em</dt>
          <dd>{formatDateTime(job.finished_at)}</dd>
        </div>
      </dl>
      {job.error ? (
        <p className="form-error" role="alert">
          {errorMessage} {errorCode}
        </p>
      ) : null}
      {job.status === "completed" ? (
        <a className="ghost-link" href="#/occurrences">
          Ver ocorrencias
        </a>
      ) : null}
    </section>
  );
}

function ConfigurationMissing() {
  return (
    <main className="center-shell">
      <section className="access-panel">
        <span className="eyebrow">Configuracao publica</span>
        <h1>Ambiente web pendente</h1>
        <p>
          Configure as variaveis publicas Vite para habilitar a verificacao de
          sessao Supabase. Nenhuma chave sensivel deve ser usada no frontend.
        </p>
        <ul className="env-list">
          {requiredPublicEnv.map((item) => (
            <li key={item.key}>
              <span>
                <strong>{item.label}</strong>
                <code>{item.key}</code>
              </span>
              <span className={item.value ? "pill ok" : "pill missing"}>
                {item.value ? "ok" : "faltando"}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function LoadingShell() {
  return (
    <main className="center-shell">
      <section className="access-panel">
        <span className="eyebrow">Sessao</span>
        <h1>Validando acesso</h1>
        <p>Carregando sessao Supabase antes de abrir o shell da aplicacao.</p>
        <div className="loading-bar" aria-label="Carregando" />
      </section>
    </main>
  );
}

function LoginShell({ error, isSubmitting, onSubmit }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    await onSubmit(email, password);
  }

  return (
    <main className="center-shell">
      <section className="login-layout">
        <div className="login-copy">
          <span className="eyebrow">MercadoIA BO Platform</span>
          <h1>Acesse o ambiente operacional</h1>
          <p>
            Use sua conta Supabase Auth para entrar. A senha e a sessao sao
            tratadas exclusivamente pelo Supabase.
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              disabled={isSubmitting}
              inputMode="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Senha
            <input
              autoComplete="current-password"
              disabled={isSubmitting}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? (
            <p className="form-error" role="alert">
              {error.message}
            </p>
          ) : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Entrando" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}

function SessionError({ error }) {
  return (
    <main className="center-shell">
      <section className="access-panel">
        <span className="eyebrow">Sessao</span>
        <h1>Falha ao validar acesso</h1>
        <p>
          A validacao de sessao encontrou um erro controlado. Verifique as
          variaveis publicas e a API local antes de navegar.
        </p>
        <code className="error-code">{error?.name ?? "SessionError"}</code>
      </section>
    </main>
  );
}
