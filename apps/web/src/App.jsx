import { useEffect, useMemo, useState } from "react";

const apiOrigin = import.meta.env.VITE_HERMES_API_ORIGIN || "http://localhost:8000";
const devAuthBootstrapEnabled = import.meta.env.VITE_ENABLE_DEV_AUTH_BOOTSTRAP !== "false";
const defaultScopes = [
  "decisions:create",
  "decisions:read",
  "executions:create",
  "executions:read",
  "audit:read",
].join(" ");

const initialDecisionForm = {
  instrument_id: "BTC-USD",
  strategy_id: "strategy-paper-001",
  portfolio_id: "portfolio-paper-001",
  market_bias: 0.45,
  volatility: 0.28,
};

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function StatCard({ label, value, tone = "default" }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Section({ title, subtitle, children, actions }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

function loadStoredValue(key, fallback) {
  return window.localStorage.getItem(key) || fallback;
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [principal, setPrincipal] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [decisionForm, setDecisionForm] = useState(initialDecisionForm);
  const [selectedDecision, setSelectedDecision] = useState("");
  const [requestedNotional, setRequestedNotional] = useState(5000);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [accessToken, setAccessToken] = useState(() => loadStoredValue("hermes.accessToken", ""));
  const [tokenDraft, setTokenDraft] = useState(() => loadStoredValue("hermes.accessToken", ""));
  const [tenantId, setTenantId] = useState(() => loadStoredValue("hermes.tenantId", "11111111-1111-1111-1111-111111111111"));
  const [principalId, setPrincipalId] = useState(() => loadStoredValue("hermes.principalId", "22222222-2222-2222-2222-222222222222"));
  const [subject, setSubject] = useState(() => loadStoredValue("hermes.subject", "privy-user-local"));
  const [scopes, setScopes] = useState(() => loadStoredValue("hermes.scopes", defaultScopes));

  const acceptedDecisions = useMemo(
    () => decisions.filter((decision) => decision.status === "ACCEPTED"),
    [decisions]
  );

  useEffect(() => {
    window.localStorage.setItem("hermes.accessToken", accessToken);
    window.localStorage.setItem("hermes.tenantId", tenantId);
    window.localStorage.setItem("hermes.principalId", principalId);
    window.localStorage.setItem("hermes.subject", subject);
    window.localStorage.setItem("hermes.scopes", scopes);
    setTokenDraft(accessToken);
  }, [accessToken, principalId, scopes, subject, tenantId]);

  async function request(path, options = {}) {
    const method = options.method || "GET";
    const headers = {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(tenantId ? { "X-Hermes-Tenant-ID": tenantId } : {}),
      ...((method !== "GET" && method !== "HEAD") ? { "Idempotency-Key": crypto.randomUUID() } : {}),
      ...(options.headers || {}),
    };

    const response = await fetch(`${apiOrigin}${path}`, {
      ...options,
      method,
      headers,
    });
    if (!response.ok) {
      const payload = await response.text();
      throw new Error(payload || `Request failed with ${response.status}`);
    }
    return response.json();
  }

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const readiness = await request("/v1/health/ready", { headers: {} });
      setHealth(readiness);

      if (!accessToken) {
        setPrincipal(null);
        setDecisions([]);
        setExecutions([]);
        setAuditEvents([]);
        return;
      }

      const [me, nextDecisions, nextExecutions, nextAudit] = await Promise.all([
        request("/v1/me"),
        request("/v1/decisions"),
        request("/v1/executions"),
        request("/v1/audit/events"),
      ]);
      setPrincipal(me);
      setDecisions(nextDecisions);
      setExecutions(nextExecutions);
      setAuditEvents(nextAudit);
      if (!selectedDecision && nextDecisions.length > 0) {
        const firstAccepted = nextDecisions.find((decision) => decision.status === "ACCEPTED");
        if (firstAccepted) {
          setSelectedDecision(firstAccepted.id);
        }
      }
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [accessToken, tenantId]);

  async function mintDevToken() {
    setAuthBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiOrigin}/v1/dev/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          principal_id: principalId,
          tenant_id: tenantId,
          subject,
          scopes: scopes.split(/\s+/).filter(Boolean),
          roles: ["tenant_admin", "trader"],
          lifetime_seconds: 28800,
        }),
      });
      if (!response.ok) {
        throw new Error((await response.text()) || `Token bootstrap failed with ${response.status}`);
      }
      const payload = await response.json();
      setAccessToken(payload.access_token);
      setTokenDraft(payload.access_token);
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setAuthBusy(false);
    }
  }

  function applyPastedToken() {
    setAccessToken(tokenDraft.trim());
    setError("");
  }

  function clearToken() {
    setAccessToken("");
    setTokenDraft("");
    setPrincipal(null);
    setDecisions([]);
    setExecutions([]);
    setAuditEvents([]);
    setDetail(null);
  }

  async function createDecision(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/v1/decision-evaluations", {
        method: "POST",
        body: JSON.stringify({
          ...decisionForm,
          market_bias: Number(decisionForm.market_bias),
          volatility: Number(decisionForm.volatility),
        }),
      });
      await refresh();
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setBusy(false);
    }
  }

  async function createExecution(event) {
    event.preventDefault();
    if (!selectedDecision) {
      setError("Choose an accepted decision before simulating execution.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request("/v1/executions", {
        method: "POST",
        body: JSON.stringify({
          decision_id: selectedDecision,
          requested_notional: Number(requestedNotional),
        }),
      });
      await refresh();
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero panel">
        <div>
          <span className="eyebrow">Hermes simulation-only MVP</span>
          <h1>Decision, risk, execution, and audit in one small loop.</h1>
          <p>
            This build is intentionally narrow: single tenant, paper venue, no live signer,
            no secrets in the browser, and no real venue credentials.
          </p>
        </div>
        <button className="ghost-button" onClick={refresh} disabled={busy}>
          {busy ? "Refreshing..." : "Refresh state"}
        </button>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      {!accessToken ? (
        <div className="warning-banner">
          Protected endpoints require a bearer token. Use the local dev bootstrap or paste a token below.
        </div>
      ) : null}

      <section className="stats-grid">
        <StatCard label="Readiness" value={health?.status || "unknown"} tone="good" />
        <StatCard label="Version" value={health?.version || health?.time?.slice(0, 19) || "unknown"} tone="accent" />
        <StatCard label="Accepted decisions" value={acceptedDecisions.length} />
        <StatCard label="Executions" value={executions.length} />
      </section>

      <section className="grid two-up">
        <Section
          title="Access"
          subtitle="Mint a local development token or paste an existing bearer token."
          actions={<span className="pill">{accessToken ? "authenticated" : "token required"}</span>}
        >
          <div className="form-grid">
            <label>
              Tenant ID
              <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
            </label>
            <label>
              Principal ID
              <input value={principalId} onChange={(event) => setPrincipalId(event.target.value)} />
            </label>
            <label>
              Subject
              <input value={subject} onChange={(event) => setSubject(event.target.value)} />
            </label>
            <label>
              Scopes
              <input value={scopes} onChange={(event) => setScopes(event.target.value)} />
            </label>
            <label>
              Access token
              <textarea
                className="auth-token"
                rows="4"
                value={tokenDraft}
                onChange={(event) => setTokenDraft(event.target.value)}
                placeholder="Paste a bearer token or mint one with the local dev bootstrap."
              />
            </label>
            <div className="inline-actions">
              {devAuthBootstrapEnabled ? (
                <button type="button" className="primary-button" onClick={mintDevToken} disabled={authBusy}>
                  {authBusy ? "Minting..." : "Mint local dev token"}
                </button>
              ) : null}
              <button type="button" className="ghost-button" onClick={applyPastedToken} disabled={authBusy}>
                Use token
              </button>
              <button type="button" className="ghost-button" onClick={clearToken} disabled={authBusy && !accessToken}>
                Clear token
              </button>
            </div>
          </div>
        </Section>

        <Section
          title="Control plane"
          subtitle="Single-tenant identity and current operator scope"
          actions={<span className="pill">{principal?.tenant_id || tenantId}</span>}
        >
          <div className="stack compact">
            <div className="kv-row"><span>Principal</span><strong>{principal?.principal_id || principalId}</strong></div>
            <div className="kv-row"><span>Roles</span><strong>{principal?.roles?.join(", ") || "-"}</strong></div>
            <div className="kv-row"><span>Scopes</span><strong>{principal?.scopes?.join(", ") || scopes}</strong></div>
            <div className="kv-row"><span>Live trading</span><strong>{String(health?.live_trading_enabled ?? false)}</strong></div>
          </div>
        </Section>
      </section>

      <section className="grid two-up">
        <Section title="Create decision" subtitle="Capture a simulated snapshot and evaluate consensus.">
          <form className="form-grid" onSubmit={createDecision}>
            <label>
              Instrument
              <input
                value={decisionForm.instrument_id}
                onChange={(event) => setDecisionForm({ ...decisionForm, instrument_id: event.target.value })}
              />
            </label>
            <label>
              Strategy
              <input
                value={decisionForm.strategy_id}
                onChange={(event) => setDecisionForm({ ...decisionForm, strategy_id: event.target.value })}
              />
            </label>
            <label>
              Portfolio
              <input
                value={decisionForm.portfolio_id}
                onChange={(event) => setDecisionForm({ ...decisionForm, portfolio_id: event.target.value })}
              />
            </label>
            <label>
              Market bias
              <input
                type="number"
                step="0.01"
                min="-1"
                max="1"
                value={decisionForm.market_bias}
                onChange={(event) => setDecisionForm({ ...decisionForm, market_bias: event.target.value })}
              />
            </label>
            <label>
              Volatility
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={decisionForm.volatility}
                onChange={(event) => setDecisionForm({ ...decisionForm, volatility: event.target.value })}
              />
            </label>
            <button type="submit" className="primary-button" disabled={busy || !accessToken}>Create decision</button>
          </form>
        </Section>

        <Section title="Simulate execution" subtitle="Run deterministic paper risk and execution on an accepted decision.">
          <form className="form-grid" onSubmit={createExecution}>
            <label>
              Accepted decision
              <select value={selectedDecision} onChange={(event) => setSelectedDecision(event.target.value)}>
                <option value="">Select a decision</option>
                {acceptedDecisions.map((decision) => (
                  <option key={decision.id} value={decision.id}>
                    {decision.instrument_id} · {decision.action} · {decision.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Requested notional
              <input
                type="number"
                min="1"
                max="100000"
                step="100"
                value={requestedNotional}
                onChange={(event) => setRequestedNotional(event.target.value)}
              />
            </label>
            <button type="submit" className="primary-button" disabled={busy || !accessToken}>Simulate execution</button>
          </form>
        </Section>
      </section>

      <section className="grid two-up">
        <Section title="Decisions" subtitle="Consensus results and supporting confidence.">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Instrument</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Support</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((decision) => (
                  <tr key={decision.id} onClick={() => setDetail(decision)}>
                    <td>{decision.instrument_id}</td>
                    <td>{decision.action}</td>
                    <td>{decision.status}</td>
                    <td>{decision.support_weight}</td>
                    <td>{decision.weighted_confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="Executions" subtitle="Paper fills and deterministic risk results.">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Execution</th>
                  <th>Side</th>
                  <th>State</th>
                  <th>Approved</th>
                  <th>Venue</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((execution) => (
                  <tr key={execution.id} onClick={() => setDetail(execution)}>
                    <td>{execution.id.slice(0, 8)}</td>
                    <td>{execution.side}</td>
                    <td>{execution.state}</td>
                    <td>{execution.approved_notional}</td>
                    <td>{execution.venue_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </section>

      <section className="grid two-up">
        <Section title="Details" subtitle="Inspect the latest record body or click a row below.">
          <pre className="code-panel">{detail ? prettyJson(detail) : "Select a decision, execution, or audit record to inspect details."}</pre>
        </Section>

        <Section title="Audit events" subtitle="Append-only operational evidence for the MVP flow.">
          <div className="audit-grid">
            {auditEvents.map((event) => (
              <button key={event.id} className="audit-card" onClick={() => setDetail(event)}>
                <span>{event.action}</span>
                <strong>{event.result}</strong>
                <small>{event.resource_type} · {event.resource_id.slice(0, 8)}</small>
              </button>
            ))}
          </div>
        </Section>
      </section>
    </main>
  );
}
