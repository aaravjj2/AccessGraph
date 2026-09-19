import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleAlert,
  FileText,
  Info,
  ShieldCheck,
  Wallet,
  ListChecks,
} from "lucide-react";
import type {
  AuthorizationResult,
  Explanation,
  MissingRequirement,
} from "../lib/contracts";
import {
  criteriaFor,
  criterionLabel,
  hasNoAssessment,
  narrative,
  statusLabel,
} from "../lib/presentation";

export function ReadinessCard({ result }: { result: AuthorizationResult }) {
  const percent = Math.round(result.authorization_readiness * 100);
  const unavailable = hasNoAssessment(result);
  return (
    <section className="readiness-card" aria-labelledby="readiness-title">
      <div className="readiness-top">
        <h2 id="readiness-title">Authorization readiness</h2>
        <Info size={16} aria-hidden="true" />
      </div>
      <div className="readiness-body">
        <div
          className="readiness-ring"
          role="img"
          aria-label={
            unavailable
              ? "Readiness unavailable"
              : `${percent}% authorization readiness`
          }
        >
          <svg viewBox="0 0 140 140" aria-hidden="true">
            <circle className="ring-track" cx="70" cy="70" r="60" />
            <circle
              className="ring-fill"
              cx="70"
              cy="70"
              r="60"
              pathLength="100"
              strokeDasharray={`${unavailable ? 0 : percent} 100`}
            />
          </svg>
          <strong>
            {unavailable ? "—" : percent}
            <small>{unavailable ? "" : "%"}</small>
          </strong>
        </div>
        <div>
          <span className="readiness-status">{statusLabel(result.status)}</span>
          <p>
            <strong>
              {result.requirements_met} of {result.requirements_total}
            </strong>
            <br />
            requirements satisfied
          </p>
        </div>
      </div>
      <p className="readiness-note">
        Criteria alignment, not a guarantee of insurer approval.
      </p>
    </section>
  );
}

export function MissingEvidenceCard({
  missing,
  onExplain,
}: {
  missing: MissingRequirement[];
  onExplain: (id: string) => void;
}) {
  if (!missing.length) return null;
  return (
    <div className="missing-evidence">
      <div className="missing-label">
        <CircleAlert size={15} />
        <span>
          {missing.length} {missing.length === 1 ? "item needs" : "items need"}{" "}
          attention
        </span>
      </div>
      {missing.map((item) => (
        <button
          className="missing-item"
          key={item.criterion_id}
          onClick={() => onExplain(item.criterion_id)}
        >
          <span>{criterionLabel(item.criterion_id)}</span>
          <ArrowUpRight size={17} />
        </button>
      ))}
    </div>
  );
}

export function NextBestActionCard({
  result,
  onExplain,
  onDocuments,
}: {
  result: AuthorizationResult;
  onExplain: (id: string) => void;
  onDocuments: () => void;
}) {
  const first = result.missing_requirements[0];
  return (
    <section className="card next-action">
      <div className="section-heading">
        <span className="eyebrow">YOUR NEXT BEST ACTION</span>
        <span className="icon-box small-icon">
          <ListChecks size={18} />
        </span>
      </div>
      <h2>
        {first
          ? first.recommended_action
          : hasNoAssessment(result)
            ? "Complete the case information"
            : "Review the findings with your care team"}
      </h2>
      <p className="muted">
        {first
          ? first.description +
            ". Review this documentation gap before preparing the authorization request."
          : "Confirm that the records and policy details are complete before moving forward."}
      </p>
      <div className="next-action-bottom">
        <MissingEvidenceCard
          missing={result.missing_requirements}
          onExplain={onExplain}
        />
        <button
          className="button secondary"
          onClick={() =>
            first ? onExplain(first.criterion_id) : onDocuments()
          }
        >
          {first ? "Review missing evidence" : "Review source documents"}
          <ArrowRight size={16} />
        </button>
      </div>
    </section>
  );
}

export function CriteriaChecklist({
  result,
  onExplain,
  onDocuments,
}: {
  result: AuthorizationResult;
  onExplain: (id: string) => void;
  onDocuments: () => void;
}) {
  const [filter, setFilter] = useState<"all" | "attention">("all");
  const criteria = criteriaFor(result);
  const visible =
    filter === "all"
      ? criteria
      : criteria.filter((item) => item.result !== "SATISFIED");
  return (
    <section className="card criteria-card">
      <div className="section-heading criteria-heading">
        <div>
          <h2>Evidence meets policy</h2>
          <p className="muted small">
            Every requirement, with the reasoning behind it.
          </p>
        </div>
        <span className="criteria-total">
          {result.requirements_met}/{result.requirements_total} matched
        </span>
      </div>
      <div className="criteria-tabs" role="group" aria-label="Filter criteria">
        <button
          aria-pressed={filter === "all"}
          onClick={() => setFilter("all")}
        >
          All criteria <span>{criteria.length}</span>
        </button>
        <button
          aria-pressed={filter === "attention"}
          onClick={() => setFilter("attention")}
        >
          Needs attention{" "}
          <span>
            {criteria.filter((item) => item.result !== "SATISFIED").length}
          </span>
        </button>
      </div>
      <div className="criteria-list">
        {criteria.map((item) => (
          <CriterionRow
            key={item.criterion_id}
            item={item}
            onExplain={onExplain}
            filteredOut={filter === "attention" && item.result === "SATISFIED"}
          />
        ))}
        {!visible.length ? (
          <p className="empty-criteria">
            {criteria.length
              ? "No flagged criteria in the available explanations."
              : "Criterion details were not included in this analysis."}
          </p>
        ) : null}
      </div>
      <div className="criteria-footnote">
        <FileText size={14} />
        <span>Policy rationale is included with each finding.</span>
        <button className="text-button" onClick={onDocuments}>
          Source documents <ArrowUpRight size={14} />
        </button>
      </div>
    </section>
  );
}

function CriterionRow({
  item,
  onExplain,
  filteredOut,
}: {
  item: Explanation;
  onExplain: (id: string) => void;
  filteredOut: boolean;
}) {
  const satisfied = item.result === "SATISFIED";
  return (
    <button
      className={`criterion-row ${satisfied ? "" : "flagged"} ${filteredOut ? "filtered-out" : ""}`}
      onClick={() => onExplain(item.criterion_id)}
      aria-label={`Explain ${criterionLabel(item.criterion_id)}`}
    >
      <span
        className={`criterion-icon ${satisfied ? "satisfied" : "attention"}`}
      >
        {satisfied ? <Check size={18} /> : <CircleAlert size={18} />}
      </span>
      <span className="criterion-description">
        <strong>{criterionLabel(item.criterion_id)}</strong>
        <span>{narrative(item.patient_evidence).text}</span>
      </span>
      <span className={`status-badge ${satisfied ? "green" : "amber"}`}>
        {satisfied
          ? "Satisfied"
          : item.result === "MISSING"
            ? "Missing evidence"
            : "Needs review"}
      </span>
      <ChevronRight size={16} />
    </button>
  );
}

export function CostEstimateCard({
  cost,
}: {
  cost: AuthorizationResult["estimated_patient_cost"];
}) {
  const format = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: cost.currency,
    maximumFractionDigits: 0,
  });
  return (
    <section className="card cost-card">
      <div className="section-heading">
        <h2>Patient cost estimate</h2>
        <Wallet size={18} />
      </div>
      <span className="small muted">Estimated out-of-pocket</span>
      <div className="cost-range">
        {format.format(cost.low)}
        <span>–</span>
        {format.format(cost.high)}
      </div>
      <span className="currency-tag">{cost.currency} · estimated range</span>
      <div className="cost-basis">
        <Info size={15} />
        <p>
          {cost.basis}. Actual costs depend on coverage, benefits, and provider
          billing.
        </p>
      </div>
    </section>
  );
}

export function IdentityVerificationCard({
  identity,
  mock,
}: {
  identity: AuthorizationResult["identity_status"];
  mock: boolean;
}) {
  return (
    <section className="card identity-card">
      <div className="section-heading">
        <h2>Trusted connections</h2>
        <ShieldCheck size={18} />
      </div>
      {[
        { label: "Provider agent", verified: identity.provider_agent_verified },
        { label: "Insurer agent", verified: identity.insurer_agent_verified },
      ].map((agent) => (
        <div className="identity-row" key={agent.label}>
          <span>{agent.label}</span>
          <span
            className={`identity-state ${agent.verified ? "verified" : ""}`}
          >
            {agent.verified ? <Check size={13} /> : <CircleAlert size={13} />}
            {agent.verified ? "Verified" : "Not verified"}
          </span>
        </div>
      ))}
      <p className="small muted">
        {mock
          ? "Verification statuses are simulated in this demo."
          : "Statuses reported by the analysis service. An unverified agent may be unavailable or could not be verified."}
      </p>
    </section>
  );
}


// The PRD demo is intentionally explicit: a human confirms ambiguous evidence,
// then a verified external agent may add the missing record.
export function DemoLifecycleCard({
  result, enabled, busy, onConfirm, onVerify, onAddEvidence,
}: {
  result: AuthorizationResult;
  enabled: boolean;
  busy: boolean;
  onConfirm: () => Promise<void>;
  onVerify: () => Promise<void>;
  onAddEvidence: () => Promise<void>;
}) {
  const instability = result.explanations.find((item) => item.criterion_id === "FUNCTIONAL_INSTABILITY");
  const pt = result.explanations.find((item) => item.criterion_id === "PT_DURATION");
  const ready = result.status === "READY_FOR_REVIEW";
  const step = ready
    ? "All requirements are met. A human must still review before submission."
    : instability?.result !== "SATISFIED"
      ? "Human review required: confirm the positive Lachman finding."
      : !result.identity_status.provider_agent_verified
        ? "Verify the PT agent before external evidence can enter the case."
        : `Verified PT agent can add the remaining documented therapy days.`;
  return (
    <section className="card next-action" aria-live="polite">
      <div className="section-heading">
        <span className="eyebrow">DEMO STATE TRANSITION</span>
        <span className="icon-box small-icon"><ShieldCheck size={18} /></span>
      </div>
      <h2>{ready ? "Case is ready for human review" : step}</h2>
      <p className="muted">
        {enabled
          ? "Each step creates an audit event and re-evaluates the policy deterministically."
          : "Set VITE_ORCHESTRATOR_URL to run the connected lifecycle. Mock mode remains read-only."}
      </p>
      {!ready ? (
        <div className="next-action-bottom">
          {instability?.result !== "SATISFIED" ? (
            <button className="button primary" disabled={!enabled || busy} onClick={() => void onConfirm()}>
              <Check size={16} /> Confirm instability finding
            </button>
          ) : !result.identity_status.provider_agent_verified ? (
            <button className="button primary" disabled={!enabled || busy} onClick={() => void onVerify()}>
              <ShieldCheck size={16} /> Verify PT agent
            </button>
          ) : (
            <button className="button primary" disabled={!enabled || busy || pt?.result === "SATISFIED"} onClick={() => void onAddEvidence()}>
              <FileText size={16} /> Add verified 14-day PT record
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}
