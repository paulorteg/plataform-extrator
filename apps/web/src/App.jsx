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

export function App() {
  const configuredCount = requiredPublicEnv.filter((item) => item.value).length;
  const isReady = configuredCount === requiredPublicEnv.length;

  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="eyebrow">MercadoIA BO Platform</div>
        <div className="layout">
          <section className="intro">
            <h1>Base web pronta para o MVP</h1>
            <p>
              Frontend inicial executável com Vite e React. Esta tela é um
              placeholder técnico para validar ambiente local, variáveis
              públicas e deploy preview antes dos fluxos de login, upload e
              revisão.
            </p>
            <div className="actions">
              <span className={isReady ? "status ready" : "status pending"}>
                {isReady ? "Ambiente configurado" : "Configuração pendente"}
              </span>
              <span className="meta">localhost:5173</span>
            </div>
          </section>

          <section className="panel" aria-label="Configuração pública">
            <h2>Variáveis públicas</h2>
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
            <p className="note">
              Somente variáveis com prefixo VITE_ são expostas ao navegador.
              Chaves sensíveis continuam restritas ao backend.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
