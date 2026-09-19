import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  Check,
  CircleAlert,
  FileText,
  Quote,
  Upload,
  X,
  Trash2,
  ArrowRight,
} from "lucide-react";
import type { Explanation, MissingRequirement } from "../lib/contracts";
import { criterionLabel, narrative } from "../lib/presentation";

function Dialog({
  title,
  children,
  onClose,
  drawer = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  drawer?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement as HTMLElement | null;
    dialog?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={drawer ? "dialog drawer" : "dialog"}
      aria-labelledby="dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) {
          const bounds = ref.current.getBoundingClientRect();
          if (
            event.clientX < bounds.left ||
            event.clientX > bounds.right ||
            event.clientY < bounds.top ||
            event.clientY > bounds.bottom
          )
            onClose();
        }
      }}
    >
      <div className="dialog-header">
        <div>
          <div className="eyebrow">ACCESSGRAPH / CASE REVIEW</div>
          <h2 id="dialog-title">{title}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
          autoFocus
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function EvidenceExplanationDrawer({
  explanation,
  missing,
  onClose,
}: {
  explanation: Explanation;
  missing?: MissingRequirement;
  onClose: () => void;
}) {
  const patient = narrative(explanation.patient_evidence);
  const policy = narrative(explanation.payer_requirement);
  const satisfied = explanation.result === "SATISFIED";
  return (
    <Dialog
      drawer
      title={criterionLabel(explanation.criterion_id)}
      onClose={onClose}
    >
      <div className="drawer-body">
        <span className={`status-badge ${satisfied ? "green" : "amber"}`}>
          {satisfied ? <Check size={13} /> : <CircleAlert size={13} />}
          {satisfied
            ? "Requirement satisfied"
            : missing
              ? "Missing evidence"
              : "Needs review"}
        </span>
        <p className="drawer-intro">Follow the evidence behind this finding.</p>
        <section className="rationale-section">
          <div className="rationale-label">
            <FileText size={17} />
            <h3>What the policy requires</h3>
          </div>
          <p>{policy.text}</p>
          <div className="source-reference">
            <Quote size={14} />
            <span>
              {policy.source ??
                "Policy source reference not supplied by the analysis service."}
            </span>
          </div>
        </section>
        <div className="evidence-connector">
          <ArrowRight size={16} />
          <span>Compared with the patient record</span>
        </div>
        <section className="rationale-section">
          <div className="rationale-label">
            <FileText size={17} />
            <h3>What the evidence shows</h3>
          </div>
          <p>{patient.text}</p>
          <div className="source-reference">
            <Quote size={14} />
            <span>
              {patient.source ??
                (missing
                  ? "No supporting source was identified in this analysis."
                  : "Clinical source reference not supplied by the analysis service.")}
            </span>
          </div>
        </section>
        <section
          className={`rationale-outcome ${satisfied ? "" : "needs-attention"}`}
        >
          <h3>
            {satisfied ? "Why this is satisfied" : "Why this needs attention"}
          </h3>
          <p>
            {missing?.description ??
              (satisfied
                ? "The analysis service marked this criterion as satisfied based on the evidence and payer requirement shown above."
                : `The analysis service reported: ${explanation.result}. Review the evidence before proceeding.`)}
          </p>
          {missing ? (
            <>
              <div className="eyebrow">RECOMMENDED ACTION</div>
              <strong>{missing.recommended_action}</strong>
              <p className="small">
                Add the note through your clinical records workflow, then re-run
                this case. Local file previews do not update the registered
                case.
              </p>
            </>
          ) : null}
        </section>
        <p className="drawer-disclaimer small muted">
          This explanation supports clinical review. It is not an insurer
          authorization decision.
        </p>
      </div>
    </Dialog>
  );
}

export type LocalRecord = {
  id: string;
  name: string;
  size: number;
  preview?: string;
};

export function DocumentsDialog({
  records,
  onRecordsChange,
  onClose,
  mock,
}: {
  records: LocalRecord[];
  onRecordsChange: (records: LocalRecord[]) => void;
  onClose: () => void;
  mock: boolean;
}) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function addFiles(files: FileList | null) {
    if (!files?.length) return;
    setError("");
    const list = [...files];
    if (
      records.length + list.length > 5 ||
      list.some(
        (file) =>
          file.size > 5 * 1024 * 1024 || !/\.(txt|pdf)$/i.test(file.name),
      )
    ) {
      setError("Choose up to 5 PDF or TXT files, no larger than 5 MB each.");
      return;
    }
    setLoading(true);
    try {
      const added = await Promise.all(
        list.map(async (file) => ({
          id: crypto.randomUUID(),
          name: file.name,
          size: file.size,
          preview: /\.txt$/i.test(file.name)
            ? (await file.text()).slice(0, 30_000)
            : undefined,
        })),
      );
      onRecordsChange([...records, ...added]);
    } catch {
      setError(
        "This file could not be opened. Please try another synthetic record.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <Dialog title="Source documents" onClose={onClose}>
      <div className="dialog-body">
        <p className="muted">
          {mock
            ? "The documents behind the shared ACL demo case."
            : "Local demo samples are available below. Source references for your live analysis appear in each criterion’s explanation."}
        </p>
        <div className="document-links">
          <a
            href="/samples/clinical-records.txt"
            target="_blank"
            rel="noreferrer"
          >
            <FileText size={21} />
            <span>
              <strong>Synthetic clinical records</strong>
              <small>MRI report · PT note · orthopedic referral</small>
            </span>
            <ArrowUpRight size={17} />
          </a>
          <a href="/samples/acl-policy.txt" target="_blank" rel="noreferrer">
            <FileText size={21} />
            <span>
              <strong>Synthetic ACL reconstruction policy</strong>
              <small>ExampleHealth PPO · Version 2026-09</small>
            </span>
            <ArrowUpRight size={17} />
          </a>
        </div>
        <h3>Preview an additional record</h3>
        <p className="small muted">
          Files stay in this browser session and are not sent for analysis. The
          current case API analyzes registered patient records only.
        </p>
        <label className={`upload-zone ${loading ? "disabled" : ""}`}>
          <Upload size={22} />
          <strong>
            {loading ? "Opening files…" : "Choose synthetic records"}
          </strong>
          <span>PDF or TXT · up to 5 MB each · 5 files maximum</span>
          <input
            type="file"
            accept=".pdf,.txt"
            multiple
            aria-label="Choose synthetic records"
            disabled={loading}
            onChange={(event) => {
              void addFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </label>
        {error ? (
          <p role="alert" className="form-error">
            {error}
          </p>
        ) : null}
        <div className="local-records">
          {records.map((record) => (
            <div className="local-record" key={record.id}>
              <div>
                <FileText size={17} />
                <strong>{record.name}</strong>
                <span className="small muted">
                  {Math.max(1, Math.round(record.size / 1024))} KB
                </span>
                <button
                  className="icon-button"
                  aria-label={`Remove ${record.name}`}
                  disabled={loading}
                  onClick={() =>
                    onRecordsChange(
                      records.filter((item) => item.id !== record.id),
                    )
                  }
                >
                  <Trash2 size={16} />
                </button>
              </div>
              {record.preview !== undefined ? (
                <details>
                  <summary>Preview text</summary>
                  <pre>{record.preview}</pre>
                </details>
              ) : (
                <p className="small muted">
                  PDF selected for local review. Document extraction is handled
                  by the clinical records workflow.
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </Dialog>
  );
}

export function GuideDialog({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title="From case to clarity" onClose={onClose}>
      <div className="dialog-body guide-body">
        <p className="muted">
          A quick walkthrough of the shared synthetic ACL case.
        </p>
        <ol>
          <li>
            <strong>Start with Synthetic Patient A.</strong>
            <p>ACL reconstruction and ExampleHealth PPO are preselected.</p>
          </li>
          <li>
            <strong>Analyze authorization readiness.</strong>
            <p>
              The demo returns 75% readiness with 3 of 4 requirements satisfied.
            </p>
          </li>
          <li>
            <strong>Find the documentation gap.</strong>
            <p>
              A recent qualifying physical exam is missing. Open the criterion
              to see the policy rationale.
            </p>
          </li>
          <li>
            <strong>Review the complete picture.</strong>
            <p>
              Explore the $1,200–$1,700 synthetic cost estimate and simulated
              provider and insurer identity statuses.
            </p>
          </li>
          <li>
            <strong>Take the next step.</strong>
            <p>
              Request the latest orthopedic physical exam note through your
              clinical workflow.
            </p>
          </li>
        </ol>
        <div className="notice">
          <CircleAlert size={19} />
          <p>
            Readiness describes the available evidence. The insurer makes the
            final authorization decision.
          </p>
        </div>
      </div>
    </Dialog>
  );
}
