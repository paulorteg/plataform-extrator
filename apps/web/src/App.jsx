import { Component, useEffect, useMemo, useState } from "react";

import {
  loadCurrentUser,
  signInWithSupabase,
  signOutFromSupabase,
} from "./lib/auth/session.js";
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
  const displayName = useMemo(
    () => sessionGate.user?.name ?? sessionGate.user?.email ?? "Usuario",
    [sessionGate.user],
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
      </section>
    </main>
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
