import {
  ArrowRight,
  ChevronDown,
  FileText,
  Plus,
  ShieldCheck,
  Sparkles,
  UserRound,
  Stethoscope,
  Building2,
  Check,
  ArrowUpRight,
} from "lucide-react";
import type { AnalyzeCaseRequest } from "../lib/contracts";

type SelectorProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

export function CaseSelector({ value, onChange, disabled }: SelectorProps) {
  return (
    <label className="field">
      <span>
        Patient case <span className="field-tag">SYNTHETIC</span>
      </span>
      <div className="select-wrap">
        <UserRound size={18} />
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          aria-label="Patient case"
        >
          <option value="P001">Synthetic Patient A · P001</option>
        </select>
        <ChevronDown size={16} />
      </div>
    </label>
  );
}
export function ProcedureSelector({
  value,
  onChange,
  disabled,
}: SelectorProps) {
  return (
    <label className="field">
      <span>Requested procedure</span>
      <div className="select-wrap">
        <Stethoscope size={18} />
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          aria-label="Requested procedure"
        >
          <option value="ACL_RECONSTRUCTION">ACL reconstruction</option>
        </select>
        <ChevronDown size={16} />
      </div>
    </label>
  );
}
export function InsurerSelector({ value, onChange, disabled }: SelectorProps) {
  return (
    <label className="field">
      <span>Insurance plan</span>
      <div className="select-wrap">
        <Building2 size={18} />
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          aria-label="Insurance plan"
        >
          <option value="ExampleHealth PPO">ExampleHealth PPO</option>
        </select>
        <ChevronDown size={16} />
      </div>
    </label>
  );
}
export function AnalyzeButton({ disabled = false }: { disabled?: boolean }) {
  return (
    <button
      className="button primary analyze-button"
      disabled={disabled}
      type="submit"
    >
      <Sparkles size={17} />
      <span>Analyze Authorization Readiness</span>
      <ArrowRight size={18} />
    </button>
  );
}

export function CaseSetup({
  request,
  onChange,
  onAnalyze,
  onDocuments,
  localFileCount,
}: {
  request: AnalyzeCaseRequest;
  onChange: (request: AnalyzeCaseRequest) => void;
  onAnalyze: () => void;
  onDocuments: () => void;
  localFileCount: number;
}) {
  return (
    <div className="setup-layout">
      <section className="card setup-card">
        <div className="section-heading">
          <div>
            <div className="eyebrow">01 / CASE DETAILS</div>
            <h2>Start with the right case</h2>
          </div>
          <div className="icon-box">
            <UserRound size={21} />
          </div>
        </div>
        <p className="muted setup-intro">
          Your clinical context, in one place.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onAnalyze();
          }}
        >
          <CaseSelector
            value={request.patient_id}
            onChange={(patient_id) => onChange({ ...request, patient_id })}
          />
          <div className="field-pair">
            <ProcedureSelector
              value={request.procedure}
              onChange={(procedure) => onChange({ ...request, procedure })}
            />
            <InsurerSelector
              value={request.insurer}
              onChange={(insurer) => onChange({ ...request, insurer })}
            />
          </div>
          <div className="record-section">
            <div className="section-heading">
              <span className="field-label">Supporting records</span>
              <button
                type="button"
                className="text-button"
                onClick={onDocuments}
              >
                <Plus size={15} /> Add / preview
              </button>
            </div>
            <button
              className="record-bundle"
              type="button"
              onClick={onDocuments}
            >
              <span className="file-icon">
                <FileText size={21} />
              </span>
              <span>
                <strong>ACL clinical record bundle</strong>
                <small>MRI report, PT note & orthopedic referral</small>
              </span>
              <span className="loaded-badge">
                <Check size={12} /> Loaded
              </span>
              <ArrowUpRight size={17} />
            </button>
            {localFileCount > 0 ? (
              <p className="small muted">
                {localFileCount} local {localFileCount === 1 ? "file" : "files"}{" "}
                added for preview only.
              </p>
            ) : null}
            <p className="small muted record-hint">
              The shared ACL case is ready to explore. Use synthetic records for
              this demo.
            </p>
          </div>
          <AnalyzeButton />
          <p className="form-footnote">
            <ShieldCheck size={14} /> An evidence-based starting point for your
            review.
          </p>
        </form>
      </section>
      <div className="setup-aside">
        <section className="clarity-card">
          <span className="small-caps">
            <span className="live-dot" /> THE COMPLETE PICTURE
          </span>
          <h2>
            Less searching.
            <br />
            More clarity.
          </h2>
          <p>
            See how patient evidence aligns with payer requirements—before you
            submit.
          </p>
          <div className="graph-illustration" aria-hidden="true">
            <div className="graph-node node-record">
              <FileText size={23} />
              <span>Clinical evidence</span>
            </div>
            <div className="graph-lines">
              <i />
              <i />
            </div>
            <div className="graph-center">
              <svg viewBox="0 0 40 40">
                <path d="m10 29 10-18 10 18M14 22h12" />
                <circle cx="20" cy="11" r="3" />
                <circle cx="10" cy="29" r="3" />
                <circle cx="30" cy="29" r="3" />
              </svg>
            </div>
            <div className="graph-node node-policy">
              <ShieldCheck size={23} />
              <span>Payer criteria</span>
            </div>
            <div className="graph-output">
              <Check size={15} /> A clear next step
            </div>
          </div>
          <div className="clarity-footer">
            <span>Connected evidence.</span>
            <span>
              Informed decisions. <ArrowUpRight size={14} />
            </span>
          </div>
        </section>
        <section className="expect-card">
          <div className="eyebrow">WHAT YOU’LL GET</div>
          <div>
            <span>01</span>
            <p>
              <strong>Know where the case stands</strong>
              <small>Readiness and a criterion-by-criterion review.</small>
            </p>
          </div>
          <div>
            <span>02</span>
            <p>
              <strong>See what needs attention</strong>
              <small>Missing evidence and a practical next action.</small>
            </p>
          </div>
          <div>
            <span>03</span>
            <p>
              <strong>Plan the patient conversation</strong>
              <small>An estimated out-of-pocket cost range.</small>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
