import {
  ChangeEvent,
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  BookOpenCheck,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  FileText,
  Fingerprint,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

type Report = {
  id: string;
  filename: string;
  status: "queued" | "processing" | "complete" | "failed";
  submitted_at: string;
  error?: string | null;
};

type Citation = {
  source_id: string;
  chunk_id?: string | null;
  label: string;
  page?: number | null;
  excerpt?: string | null;
};

type Finding = {
  id: string;
  title: string;
  summary: string;
  uncertainty?: string | null;
  citations: Citation[];
};

type Recommendation = {
  id: string;
  summary: string;
  rationale: string;
  assumptions: string[];
  limitations: string[];
  sensitivity: string;
  status: string;
  citations: Citation[];
  decisions?: { outcome: string; reason?: string | null; created_at: string }[];
};

type Analysis = {
  report_id: string;
  status: string;
  findings: Finding[];
  recommendations: Recommendation[];
  limitations: string[];
};

type QuestionAnswer = {
  id: string;
  question: string;
  answer: string;
  citations: Citation[];
  limitations: string[];
  created_at: string;
};

type Approval = Recommendation;
type View = "overview" | "reports" | "approvals";

async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(result?.detail ?? `Request failed (${response.status}).`);
  }
  return result as T;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase().replaceAll("_", " ");
  return <span className={`status-pill status-${status.toLowerCase()}`}>{normalized}</span>;
}

export default function App() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [view, setView] = useState<View>("overview");
  const [reports, setReports] = useState<Report[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [question, setQuestion] = useState("");
  const [questionHistory, setQuestionHistory] = useState<QuestionAnswer[]>([]);
  const [sourceText, setSourceText] = useState<{
    label: string;
    page: number | null;
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selected = useMemo(
    () => reports.find((report) => report.id === selectedReport) ?? null,
    [reports, selectedReport],
  );

  const loadWorkspace = useCallback(async (accessToken: string) => {
    const [reportResult, approvalResult] = await Promise.allSettled([
      request<Report[]>(accessToken, "/reports"),
      request<Approval[]>(accessToken, "/approvals"),
    ]);
    if (reportResult.status === "rejected") throw reportResult.reason;
    setReports(reportResult.value);
    if (approvalResult.status === "fulfilled") {
      setApprovals(approvalResult.value);
    } else if (!String(approvalResult.reason).includes("Approver permission")) {
      setError(String(approvalResult.reason));
    }
  }, []);

  useEffect(() => {
    if (!connected || !token) return;
    const timer = window.setInterval(() => {
      void loadWorkspace(token).catch((cause: unknown) => setError(String(cause)));
    }, 6000);
    return () => window.clearInterval(timer);
  }, [connected, loadWorkspace, token]);

  useEffect(() => {
    if (!token || !selectedReport) {
      setAnalysis(null);
      setQuestionHistory([]);
      return;
    }
    let cancelled = false;
    setAnalysis(null);
    setQuestionHistory([]);
    const loadAnalysis = () => {
      void request<Analysis>(token, `/reports/${selectedReport}/analysis`)
        .then((result) => {
          if (!cancelled) setAnalysis(result);
        })
        .catch((cause: unknown) => {
          if (!cancelled) setError(String(cause));
        });
    };
    loadAnalysis();
    void request<QuestionAnswer[]>(token, `/reports/${selectedReport}/questions`)
      .then((questions) => {
        if (!cancelled) setQuestionHistory(questions);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(String(cause));
      });
    const timer = window.setInterval(loadAnalysis, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedReport, token]);

  async function connect(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await loadWorkspace(tokenInput.trim());
      setToken(tokenInput.trim());
      setConnected(true);
      setNotice("Secure workspace connected.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not connect to the workspace.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadReport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !token) return;
    if (file.type !== "application/pdf") {
      setError("Choose a PDF report to upload.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    setError("");
    try {
      const created = await request<Report>(token, "/reports", { method: "POST", body: form });
      await loadWorkspace(token);
      setSelectedReport(created.id);
      setView("reports");
      setNotice("Report received. Analysis will appear here when processing finishes.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The report could not be uploaded.");
    } finally {
      setBusy(false);
    }
  }

  async function openCitation(citation: Citation) {
    if (!token || (!citation.page && !citation.chunk_id)) return;
    try {
      const source = await request<{ label: string; page: number | null; text: string }>(
        token,
        citation.page
          ? `/reports/${citation.source_id}/citations/${citation.page}`
          : `/knowledge-sources/${citation.source_id}/citations/${citation.chunk_id}`,
      );
      setSourceText(source);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The cited source could not be opened.");
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!selectedReport || !question.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await request<Omit<QuestionAnswer, "id" | "question" | "created_at">>(
        token,
        `/reports/${selectedReport}/questions`,
        { method: "POST", body: JSON.stringify({ question }) },
      );
      setQuestionHistory((current) => [
        {
          ...result,
          id: crypto.randomUUID(),
          question: question.trim(),
          created_at: new Date().toISOString(),
        },
        ...current,
      ]);
      setQuestion("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The question could not be answered.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(item: Approval, outcome: "approved" | "rejected") {
    const reason = window.prompt(`Optional reason for ${outcome}:`) ?? "";
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await request(token, `/recommendations/${item.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ outcome, reason: reason.trim() || null }),
      });
      setApprovals((current) => current.filter((approval) => approval.id !== item.id));
      setNotice(`Recommendation ${outcome}. The decision has been recorded.`);
      await loadWorkspace(token);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The approval decision could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const doneCount = reports.filter((report) => report.status === "complete").length;
  const workingCount = reports.filter((report) => ["queued", "processing"].includes(report.status)).length;

  if (!connected) {
    return (
      <main className="connect-screen">
        <div className="connect-glow connect-glow-one" />
        <div className="connect-glow connect-glow-two" />
        <div className="connect-card">
          <Brand />
          <div className="connect-copy">
            <span className="eyebrow"><Fingerprint size={14} /> PRIVATE ANALYSIS WORKSPACE</span>
            <h1>Clarity for the<br /><span>decisions that matter.</span></h1>
            <p>Bring financial reports into focus with evidence-led analysis and human oversight at every critical step.</p>
          </div>
          <form onSubmit={connect} className="connect-form">
            <label htmlFor="access-token">Secure access token</label>
            <input
              id="access-token"
              type="password"
              autoComplete="off"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              placeholder="Paste your organization-issued token"
              required
            />
            <button className="button button-primary" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <LockKeyhole size={16} />}
              Connect securely
              <ArrowRight size={16} />
            </button>
            {error && <p className="inline-error" role="alert">{error}</p>}
          </form>
          <div className="connect-foot"><ShieldCheck size={15} /> Your token stays in this browser session.</div>
        </div>
        <div className="connect-visual" aria-hidden="true">
          <div className="visual-orbit orbit-a" />
          <div className="visual-orbit orbit-b" />
          <div className="visual-core"><Sparkles size={30} /></div>
          <div className="visual-card visual-card-top"><span className="mini-mark">↗</span><div><b>Evidence first</b><small>Every insight traceable</small></div></div>
          <div className="visual-card visual-card-bottom"><span className="mini-check"><Check size={14} /></span><div><b>Human oversight</b><small>Decisions stay yours</small></div></div>
        </div>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <NavButton active={view === "overview"} onClick={() => setView("overview")} icon={<LayoutDashboard size={18} />} label="Overview" />
          <NavButton active={view === "reports"} onClick={() => setView("reports")} icon={<FileText size={18} />} label="Reports" badge={reports.length || undefined} />
          <NavButton active={view === "approvals"} onClick={() => setView("approvals")} icon={<ShieldCheck size={18} />} label="Approvals" badge={approvals.length || undefined} />
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-security">
          <div className="security-icon"><ShieldCheck size={17} /></div>
          <div><strong>Private by design</strong><span>Sources stay permission-scoped</span></div>
        </div>
        <button className="profile-row" onClick={() => { setConnected(false); setToken(""); setTokenInput(""); }}>
          <div className="avatar">FA</div>
          <div className="profile-copy"><strong>Financial analyst</strong><span>Workspace session</span></div>
          <ChevronDown size={16} />
        </button>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-sep">/</span><strong>{viewLabel(view)}</strong></div>
          <div className="top-actions">
            <span className="live-indicator"><i /> Connected</span>
            <button className="icon-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="avatar avatar-small">FA</div>
          </div>
        </header>

        <div className="page-container">
          <div className="page-heading">
            <div>
              <span className="eyebrow"><Sparkles size={14} /> FINANCIAL INTELLIGENCE</span>
              <h1>{view === "overview" ? "Good morning." : viewLabel(view)}</h1>
              <p>{view === "overview" ? "A clearer view of your financial landscape starts here." : pageSubtitle(view)}</p>
            </div>
            <label className={`button button-primary upload-button ${busy ? "disabled" : ""}`}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <Upload size={17} />}
              Add report
              <input type="file" accept="application/pdf,.pdf" onChange={uploadReport} disabled={busy} />
            </label>
          </div>

          {(error || notice) && (
            <div className={`feedback ${error ? "feedback-error" : "feedback-success"}`} role={error ? "alert" : "status"}>
              {error ? <CircleAlert size={17} /> : <BadgeCheck size={17} />}
              <span>{error || notice}</span>
              <button aria-label="Dismiss message" onClick={() => { setError(""); setNotice(""); }}><X size={16} /></button>
            </div>
          )}

          {view === "overview" && (
            <>
              <section className="metric-grid" aria-label="Workspace summary">
                <MetricCard icon={<FileText size={17} />} label="Reports analyzed" value={String(doneCount).padStart(2, "0")} detail={`${reports.length} total reports`} accent="blue" />
                <MetricCard icon={<Activity size={17} />} label="In progress" value={String(workingCount).padStart(2, "0")} detail="Analysis queue" accent="amber" />
                <MetricCard icon={<ShieldCheck size={17} />} label="Need your review" value={String(approvals.length).padStart(2, "0")} detail="Human approval required" accent="green" />
              </section>
              <section className="content-grid">
                <div className="panel report-panel">
                  <PanelHeading icon={<FileText size={17} />} title="Recent reports" action={<button className="text-action" onClick={() => setView("reports")}>View all <ArrowRight size={14} /></button>} />
                  {reports.length ? (
                    <div className="report-list">
                      {reports.slice(0, 5).map((report, index) => (
                        <ReportRow key={report.id} report={report} index={index} onClick={() => { setSelectedReport(report.id); setView("reports"); }} />
                      ))}
                    </div>
                  ) : <EmptyState icon={<BookOpenCheck size={21} />} title="Your analysis workspace is ready" detail="Add a report to surface key figures, risks, and cited evidence." />}
                </div>
                <div className="panel review-panel">
                  <PanelHeading icon={<ShieldCheck size={17} />} title="Human review" action={<button className="text-action" onClick={() => setView("approvals")}>Open queue <ArrowRight size={14} /></button>} />
                  {approvals.length ? (
                    <div className="approval-preview">
                      <span className="review-tag"><span /> ACTION REQUIRED</span>
                      <h3>{approvals[0].summary}</h3>
                      <p>{approvals[0].rationale}</p>
                      <div className="review-meta"><Clock3 size={14} /> Pending your review <span>•</span> Evidence attached</div>
                      <button className="button button-secondary" onClick={() => setView("approvals")}>Review recommendation <ArrowRight size={15} /></button>
                    </div>
                  ) : <EmptyState icon={<ShieldCheck size={21} />} title="No decisions waiting" detail="Sensitive recommendations will appear here for your review." />}
                </div>
              </section>
              <section className="trust-strip"><div className="trust-mark"><ShieldCheck size={18} /></div><p><strong>Evidence before action.</strong> Findings are linked to source passages, and sensitive decisions remain yours to approve.</p><span>BUILT FOR CONFIDENCE</span></section>
            </>
          )}

          {view === "reports" && (
            <section className="reports-layout">
              <div className="panel reports-index">
                <PanelHeading icon={<FileText size={17} />} title="Your reports" detail={`${reports.length} documents`} />
                {reports.length ? reports.map((report, index) => (
                  <ReportRow key={report.id} report={report} index={index} selected={report.id === selectedReport} onClick={() => setSelectedReport(report.id)} />
                )) : <EmptyState icon={<Upload size={21} />} title="No reports yet" detail="Upload a PDF financial report to start your first analysis." />}
              </div>
              <div className="panel analysis-panel">
                {!selected ? <EmptyState icon={<Search size={21} />} title="Select a report" detail="Choose a report to review its processing status and analysis." /> : (
                  <>
                    <div className="analysis-title-row">
                      <div className="document-icon"><FileText size={20} /></div>
                      <div className="analysis-title"><h2>{selected.filename}</h2><span>Added {formatDate(selected.submitted_at)}</span></div>
                      <StatusPill status={analysis?.status ?? selected.status} />
                    </div>
                    {selected.error && <div className="limitation-box"><CircleAlert size={16} /><span>{selected.error}</span></div>}
                    {!analysis || ["queued", "running"].includes(analysis.status) ? (
                      <div className="processing-state"><LoaderCircle className="spin" size={23} /><h3>Finding the signal in the numbers</h3><p>Your report is being reviewed. This view refreshes automatically.</p></div>
                    ) : analysis.status === "failed" ? (
                      <div className="limitation-box"><CircleAlert size={17} /><span>Analysis did not complete. Check the report status or contact your workspace administrator.</span></div>
                    ) : (
                      <>
                        <div className="section-title"><span>01</span><div><h3>Key findings</h3><p>Material information with a direct line to its source.</p></div></div>
                        {analysis.findings.length ? analysis.findings.map((finding) => (
                          <article className="finding-card" key={finding.id}>
                            <h4>{finding.title}</h4><p>{finding.summary}</p>
                            {finding.uncertainty && <div className="uncertainty"><CircleAlert size={14} /> {finding.uncertainty}</div>}
                            <CitationList citations={finding.citations} onOpen={openCitation} />
                          </article>
                        )) : <p className="quiet-copy">No material findings were returned for this report.</p>}
                        {analysis.recommendations.length > 0 && (
                          <div className="section-title section-spaced"><span>02</span><div><h3>Recommendations</h3><p>Evidence-led proposals; sensitive actions are not decisions.</p></div></div>
                        )}
                        {analysis.recommendations.map((item) => (
                          <article className="recommendation-card" key={item.id}>
                            <div className="recommendation-head"><span className="review-tag"><span /> HUMAN REVIEW</span><StatusPill status={item.status} /></div>
                            <h4>{item.summary}</h4><p>{item.rationale}</p>
                            {item.limitations.length > 0 && <div className="uncertainty"><CircleAlert size={14} /> {item.limitations.join(" ")}</div>}
                              {item.decisions?.map((decision, index) => <div className="decision-history" key={`${decision.created_at}-${index}`}><BadgeCheck size={14} /><span>{decision.outcome} · {formatDate(decision.created_at)}{decision.reason ? ` · ${decision.reason}` : ""}</span></div>)}
                            <CitationList citations={item.citations} onOpen={openCitation} />
                          </article>
                        ))}
                        {analysis.limitations.map((item, index) => <p className="quiet-copy" key={index}>{item}</p>)}
                        <form className="ask-form" onSubmit={ask}>
                          <div className="ask-header"><MessageSquareText size={16} /><div><strong>Ask this report</strong><span>Answers are grounded in permitted sources.</span></div></div>
                          <div className="ask-input-row"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about a figure, risk, or comparison…" aria-label="Ask a question about this report" /><button className="icon-submit" disabled={busy || !question.trim()} aria-label="Submit question">{busy ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}</button></div>
                          {questionHistory.map((item) => <div className="answer-card" key={item.id}><h4>{item.question}</h4><p>{item.answer}</p><CitationList citations={item.citations} onOpen={openCitation} />{item.limitations.map((limitation) => <small key={limitation}>{limitation}</small>)}</div>)}
                        </form>
                      </>
                    )}
                  </>
                )}
              </div>
            </section>
          )}

          {view === "approvals" && (
            <section className="approval-list">
              <div className="approval-intro"><div className="approval-intro-icon"><ShieldCheck size={21} /></div><div><h2>Thoughtful decisions take a human.</h2><p>Review the evidence and rationale before recording a decision. Your decision and reason are retained in the audit history.</p></div><span className="queue-count">{approvals.length}<small>pending</small></span></div>
              {approvals.length ? approvals.map((item) => (
                <article className="panel approval-card" key={item.id}>
                  <div className="recommendation-head"><span className="review-tag"><span /> SENSITIVE RECOMMENDATION</span><StatusPill status={item.status} /></div>
                  <h3>{item.summary}</h3><p className="approval-rationale">{item.rationale}</p>
                  {item.assumptions.length > 0 && <div className="assumptions"><strong>Assumptions</strong><ul>{item.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul></div>}
                  {item.limitations.length > 0 && <div className="limitation-box"><CircleAlert size={16} /><span>{item.limitations.join(" ")}</span></div>}
                  <CitationList citations={item.citations} onOpen={openCitation} />
                  <div className="approval-actions"><span><LockKeyhole size={14} /> Decision is recorded to the review history</span><div><button className="button button-reject" onClick={() => void decide(item, "rejected")} disabled={busy}><X size={15} /> Reject</button><button className="button button-approve" onClick={() => void decide(item, "approved")} disabled={busy}><Check size={15} /> Approve</button></div></div>
                </article>
              )) : <div className="panel empty-approvals"><div className="empty-icon"><BadgeCheck size={24} /></div><h3>You're all caught up.</h3><p>There are no recommendations awaiting your approval right now.</p></div>}
            </section>
          )}
        </div>
        <footer className="page-footer"><span>LEDGERLINE INTELLIGENCE</span><span>Analysis supports review. Decisions remain human.</span></footer>
      </main>
      {sourceText && <SourceDrawer source={sourceText} onClose={() => setSourceText(null)} />}
      <div className="mobile-nav" aria-label="Mobile navigation">
        <NavButton active={view === "overview"} onClick={() => setView("overview")} icon={<LayoutDashboard size={19} />} label="Home" />
        <NavButton active={view === "reports"} onClick={() => setView("reports")} icon={<FileText size={19} />} label="Reports" />
        <NavButton active={view === "approvals"} onClick={() => setView("approvals")} icon={<ShieldCheck size={19} />} label="Review" badge={approvals.length || undefined} />
      </div>
    </div>
  );
}

function Brand() {
  return <div className="brand"><div className="brand-icon"><Activity size={19} strokeWidth={2.1} /></div><div><strong>ledgerline<span>.</span></strong><small>FINANCIAL INTELLIGENCE</small></div></div>;
}

function NavButton({ active, onClick, icon, label, badge }: { active: boolean; onClick: () => void; icon: ReactNode; label: string; badge?: number }) {
  return <button className={`nav-button ${active ? "nav-active" : ""}`} onClick={onClick}>{icon}<span>{label}</span>{badge !== undefined && <b>{badge}</b>}</button>;
}

function MetricCard({ icon, label, value, detail, accent }: { icon: ReactNode; label: string; value: string; detail: string; accent: string }) {
  return <article className="metric-card"><div className={`metric-icon metric-${accent}`}>{icon}</div><span className="metric-label">{label}</span><div className="metric-value">{value}</div><span className="metric-detail"><i />{detail}</span><ArrowUpRight className="metric-arrow" size={16} /></article>;
}

function PanelHeading({ icon, title, detail, action }: { icon: ReactNode; title: string; detail?: string; action?: ReactNode }) {
  return <div className="panel-heading"><div className="panel-heading-icon">{icon}</div><div><h2>{title}</h2>{detail && <span>{detail}</span>}</div>{action}</div>;
}

function ReportRow({ report, index, selected, onClick }: { report: Report; index: number; selected?: boolean; onClick: () => void }) {
  return <button className={`report-row ${selected ? "report-selected" : ""}`} onClick={onClick}><div className={`file-tile file-tile-${index % 3}`}><FileText size={17} /></div><div className="report-row-copy"><strong>{report.filename}</strong><span>{formatDate(report.submitted_at)} <i /> PDF document</span></div><StatusPill status={report.status} /><ArrowRight className="row-arrow" size={15} /></button>;
}

function CitationList({ citations, onOpen }: { citations: Citation[]; onOpen: (citation: Citation) => void }) {
  if (!citations.length) return <div className="citation-missing"><CircleAlert size={14} /> No source citation supplied</div>;
  return <div className="citation-list">{citations.map((citation, index) => <button key={`${citation.source_id}-${citation.chunk_id}-${citation.page}-${index}`} className="citation-button" onClick={() => onOpen(citation)} disabled={!citation.page && !citation.chunk_id}><BookOpenCheck size={14} /><span>{citation.label}{citation.page ? ` · p. ${citation.page}` : " · source"}</span><ArrowUpRight size={13} /></button>)}</div>;
}

function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return <div className="empty-state"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{detail}</p></div>;
}

function SourceDrawer({ source, onClose }: { source: { label: string; page: number | null; text: string }; onClose: () => void }) {
  const location = source.page ? `Page ${source.page}` : "Knowledge source excerpt";
  return <div className="drawer-backdrop" role="presentation" onClick={onClose}><aside className="source-drawer" role="dialog" aria-modal="true" aria-label="Cited source passage" onClick={(event) => event.stopPropagation()}><div className="drawer-heading"><div><span className="eyebrow">SOURCE REFERENCE</span><h2>{source.label}</h2><p>{location}</p></div><button className="icon-button" onClick={onClose} aria-label="Close source"><X size={18} /></button></div><div className="source-page"><div className="source-page-label">{location.toUpperCase()}</div><p>{source.text}</p></div><div className="drawer-foot"><ShieldCheck size={15} /> Source access was checked for this session.</div></aside></div>;
}

function viewLabel(view: View) {
  return view === "overview" ? "Overview" : view === "reports" ? "Reports" : "Approvals";
}

function pageSubtitle(view: View) {
  return view === "reports" ? "Inspect analysis, citations, and the evidence behind each finding." : "Review sensitive recommendations before they become decisions.";
}
