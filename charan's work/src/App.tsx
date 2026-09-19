import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  FileText,
  HelpCircle,
  Layers3,
  Leaf,
  Menu,
  Printer,
  ShieldCheck,
  X,
} from "lucide-react";
import { CaseSetup } from "./components/CaseSetup";
import { ProcessingStepper } from "./components/ProcessingStepper";
import {
  CostEstimateCard,
  CriteriaChecklist,
  DemoLifecycleCard,
  IdentityVerificationCard,
  NextBestActionCard,
  ReadinessCard,
} from "./components/ResultCards";
import {
  DocumentsDialog,
  EvidenceExplanationDrawer,
  GuideDialog,
  type LocalRecord,
} from "./components/Dialogs";
import {
  AnalysisError,
  addVerifiedPtEvidence,
  analyzeCase,
  confirmInstability,
  errorMessages,
  verifyPtAgent,
  isMockMode,
} from "./lib/api";
import type { AnalyzeCaseRequest, AuthorizationResult } from "./lib/contracts";
import { analysisNotice, criteriaFor } from "./lib/presentation";
import initialRequest from "./mocks/analyzeCaseRequest.json";

type Stage = "setup" | "processing" | "results";
const minimumAnimationMs = 3000;

export default function App() {
  const [request, setRequest] = useState<AnalyzeCaseRequest>(initialRequest);
  const [stage, setStage] = useState<Stage>("setup");
  const [result, setResult] = useState<AuthorizationResult | null>(null);
  const [error, setError] = useState<AnalysisError | null>(null);
  const [dialog, setDialog] = useState<"documents" | "guide" | null>(null);
  const [selectedCriterion, setSelectedCriterion] = useState<string | null>(
    null,
  );
  const [records, setRecords] = useState<LocalRecord[]>([]);
  const [mobileNav, setMobileNav] = useState(false);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      controller.current?.abort();
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  useEffect(() => {
    if (stage === "results") heading.current?.focus();
  }, [stage]);

  async function runAnalysis() {
    controller.current?.abort();
    if (timer.current) clearTimeout(timer.current);
    const current = new AbortController();
    controller.current = current;
    setError(null);
    setResult(null);
    setSelectedCriterion(null);
    setStage("processing");
    const started = Date.now();
    try {
      const response = await analyzeCase(request, { signal: current.signal });
      await new Promise<void>((resolve) => {
        timer.current = setTimeout(
          resolve,
          Math.max(0, minimumAnimationMs - (Date.now() - started)),
        );
        current.signal.addEventListener(
          "abort",
          () => {
            if (timer.current) clearTimeout(timer.current);
            resolve();
          },
          { once: true },
        );
      });
      if (current.signal.aborted) return;
      setResult(response);
      setStage("results");
    } catch (cause) {
      if (current.signal.aborted) return;
      setError(
        cause instanceof AnalysisError
          ? cause
          : new AnalysisError("UNAVAILABLE"),
      );
      setStage("setup");
    }
  }
  async function runLifecycleAction(
    action: "confirm" | "verify" | "evidence",
  ) {
    if (!result) return;
    setLifecycleBusy(true);
    setError(null);
    try {
      const next =
        action === "confirm"
          ? await confirmInstability(request)
          : action === "evidence"
            ? await addVerifiedPtEvidence(request)
            : (await verifyPtAgent(), await analyzeCase(request));
      setResult(next);
    } catch (cause) {
      setError(cause instanceof AnalysisError ? cause : new AnalysisError("UNAVAILABLE"));
    } finally {
      setLifecycleBusy(false);
    }
  }
  function returnToSetup() {
    controller.current?.abort();
    setSelectedCriterion(null);
    setStage("setup");
    setMobileNav(false);
  }
  function openDocuments() {
    setDialog("documents");
    setMobileNav(false);
  }
  const explanation = result
    ? criteriaFor(result).find(
        (item) => item.criterion_id === selectedCriterion,
      )
    : undefined;
  const notice = result ? analysisNotice(result) : null;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to case review
      </a>
      {mobileNav ? (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      ) : null}
      <aside className={`sidebar ${mobileNav ? "nav-open" : ""}`}>
        <a
          className="brand"
          href="#main-content"
          aria-label="AccessGraph home"
          onClick={returnToSetup}
        >
          <svg className="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
            <rect width="40" height="40" rx="11" />
            <path d="m11 28 9-17 9 17M15 21h10" />
            <circle cx="20" cy="11" r="2.6" />
            <circle cx="11" cy="28" r="2.6" />
            <circle cx="29" cy="28" r="2.6" />
          </svg>
          <span>
            AccessGraph<span className="brand-period">.</span>
          </span>
        </a>
        <div className="workspace-switch">
          <span className="workspace-avatar">
            <Activity size={19} />
          </span>
          <span>
            <strong>Clinical workspace</strong>
            <small>Orthopedic care</small>
          </span>
        </div>
        <div className="nav-section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className="nav-item selected"
            onClick={() => {
              if (stage !== "results") returnToSetup();
              setMobileNav(false);
            }}
            aria-current="page"
          >
            <ClipboardList size={18} />
            Case review
            <span className="nav-indicator" />
          </button>
          <button className="nav-item" onClick={openDocuments}>
            <FileText size={18} />
            Source documents
          </button>
          <button
            className="nav-item"
            onClick={() => {
              setDialog("guide");
              setMobileNav(false);
            }}
          >
            <BookOpen size={18} />
            Demo walkthrough
            <ArrowUpRight size={14} />
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="purpose-note">
            <span className="purpose-icon">
              <Leaf size={17} />
            </span>
            <strong>
              Less friction.
              <br />
              More patient care.
            </strong>
            <p>A clearer path from evidence to action.</p>
          </div>
          <button
            className="nav-item help-button"
            onClick={() => {
              setDialog("guide");
              setMobileNav(false);
            }}
          >
            <HelpCircle size={18} />
            How it works
            <ArrowUpRight size={14} />
          </button>
          <div className="workspace-profile">
            <div className="avatar">CT</div>
            <div>
              <strong>Care team</strong>
              <small>HCP workspace</small>
            </div>
            <ShieldCheck size={17} />
          </div>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label={mobileNav ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileNav}
              onClick={() => setMobileNav(!mobileNav)}
            >
              {mobileNav ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>Case review</strong>
          </div>
          <div className="topbar-right">
            <span className="environment-badge">
              <span />
              {isMockMode ? "Demo workspace" : "Connected workspace"}
            </span>
            <span className="topbar-divider" />
            <div
              className="avatar small-avatar"
              role="img"
              aria-label="Care team"
            >
              CT
            </div>
          </div>
        </header>
        <main id="main-content" className="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="heading-line" />
                {stage === "results"
                  ? "YOUR CASE, CONNECTED"
                  : "CLARITY BEFORE THE NEXT STEP"}
              </div>
              <h1 ref={heading} tabIndex={-1}>
                {stage === "results"
                  ? "Your authorization picture."
                  : "A clearer path to authorization."}
              </h1>
              <p className="muted">
                {stage === "results"
                  ? "The evidence, the gaps, and what to do next. All in one place."
                  : "Turn clinical evidence into a confident next step for your patient."}
              </p>
            </div>
            {stage === "results" ? (
              <button
                className="button secondary print-button"
                onClick={() => window.print()}
              >
                <Printer size={16} />
                Print summary
              </button>
            ) : (
              <span className="page-label">
                <Layers3 size={15} /> PRIOR AUTHORIZATION
              </span>
            )}
          </div>
          <div
            className="workflow-bar"
            role="group"
            aria-label="Review progress"
          >
            <div className={stage === "setup" ? "current" : "done"}>
              <span>01</span>Case details
            </div>
            <i />
            <div
              className={
                stage === "processing"
                  ? "current"
                  : stage === "results"
                    ? "done"
                    : ""
              }
            >
              <span>02</span>Evidence analysis
            </div>
            <i />
            <div className={stage === "results" ? "current" : ""}>
              <span>03</span>Readiness & next steps
            </div>
          </div>
          {error ? (
            <div className="error-banner" role="alert">
              <CircleAlert size={22} />
              <div>
                <strong>{errorMessages[error.code].title}</strong>
                <p>{errorMessages[error.code].detail}</p>
              </div>
              <button
                className="text-button"
                onClick={() => void runAnalysis()}
              >
                Try again
                <ArrowRight size={15} />
              </button>
            </div>
          ) : null}
          {stage === "setup" ? (
            <CaseSetup
              request={request}
              onChange={setRequest}
              onAnalyze={() => void runAnalysis()}
              onDocuments={openDocuments}
              localFileCount={records.length}
            />
          ) : null}
          {stage === "processing" ? (
            <ProcessingStepper onCancel={returnToSetup} />
          ) : null}
          {stage === "results" && result ? (
            <div className="results">
              <div className="case-context">
                <div className="patient-avatar">PA</div>
                <div>
                  <strong>Synthetic Patient A</strong>
                  <span>
                    Patient {result.patient_id}
                    <b>·</b>Synthetic case
                  </span>
                </div>
                <span className="context-divider" />
                <span className="context-procedure">ACL reconstruction</span>
                <span className="context-plan">{request.insurer}</span>
                <button
                  className="text-button edit-case"
                  onClick={returnToSetup}
                >
                  <ArrowLeft size={14} />
                  Edit case
                </button>
              </div>
              {notice ? (
                <div className="notice" role="status">
                  <CircleAlert size={20} />
                  <div>
                    <strong>{notice.title}</strong>
                    <p>{notice.detail}</p>
                  </div>
                </div>
              ) : null}
              <div className="result-top-grid">
                <ReadinessCard result={result} />
                <NextBestActionCard
                  result={result}
                  onExplain={setSelectedCriterion}
                  onDocuments={openDocuments}
                />
              </div>
              <DemoLifecycleCard
                result={result}
                enabled={!isMockMode}
                busy={lifecycleBusy}
                onConfirm={() => runLifecycleAction("confirm")}
                onVerify={() => runLifecycleAction("verify")}
                onAddEvidence={() => runLifecycleAction("evidence")}
              />
              <div className="result-detail-grid">
                <CriteriaChecklist
                  result={result}
                  onExplain={setSelectedCriterion}
                  onDocuments={openDocuments}
                />
                <div className="result-aside">
                  <CostEstimateCard cost={result.estimated_patient_cost} />
                  <IdentityVerificationCard
                    identity={result.identity_status}
                    mock={isMockMode}
                  />
                </div>
              </div>
              <div className="result-bottom">
                <span>
                  <ShieldCheck size={15} />
                  Your clinical judgment stays at the center.
                </span>
                <button
                  className="text-button"
                  onClick={() => void runAnalysis()}
                >
                  Run analysis again
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          ) : null}
          <footer className="page-footer">
            <span>
              ACCESSGRAPH<span className="footer-dot"> / </span>Evidence to
              action.
            </span>
            <span>
              {isMockMode
                ? "Synthetic data. Real possibilities."
                : "Decision support for your clinical workflow."}
            </span>
          </footer>
        </main>
      </div>
      {dialog === "documents" ? (
        <DocumentsDialog
          records={records}
          onRecordsChange={setRecords}
          onClose={() => setDialog(null)}
          mock={isMockMode}
        />
      ) : null}
      {dialog === "guide" ? (
        <GuideDialog onClose={() => setDialog(null)} />
      ) : null}
      {explanation ? (
        <EvidenceExplanationDrawer
          explanation={explanation}
          missing={result?.missing_requirements.find(
            (item) => item.criterion_id === selectedCriterion,
          )}
          onClose={() => setSelectedCriterion(null)}
        />
      ) : null}
    </div>
  );
}
