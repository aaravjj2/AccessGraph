import { useEffect, useState } from "react";
import { Check, LoaderCircle, ArrowRight } from "lucide-react";

const steps = [
  "Reading clinical evidence",
  "Reading payer policy",
  "Matching criteria",
  "Estimating patient cost",
  "Verifying trusted agents",
  "Generating recommendation",
];

export function ProcessingStepper({ onCancel }: { onCancel: () => void }) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const interval = window.setInterval(
      () => setActive((value) => Math.min(value + 1, steps.length - 1)),
      480,
    );
    return () => window.clearInterval(interval);
  }, []);
  return (
    <section
      className="card processing-card"
      aria-busy="true"
      aria-label="Analyzing authorization readiness"
    >
      <div className="processing-symbol">
        <LoaderCircle className="spin" size={28} />
      </div>
      <div className="eyebrow">CONNECTING THE DOTS</div>
      <h2>A clearer picture is on its way.</h2>
      <p className="muted">
        Bringing the evidence, requirements, and next steps together.
      </p>
      <ol className="processing-steps">
        {steps.map((step, index) => (
          <li
            key={step}
            className={
              index < active ? "complete" : index === active ? "active" : ""
            }
          >
            <span>
              {index < active ? (
                <Check size={16} />
              ) : index === active ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                String(index + 1).padStart(2, "0")
              )}
            </span>
            <span>{step}</span>
            {index === active ? <ArrowRight size={15} /> : null}
          </li>
        ))}
      </ol>
      <p className="small muted" role="status">
        {active === steps.length - 1
          ? "Waiting for the completed analysis…"
          : "Analysis in progress…"}{" "}
        Steps illustrate the workflow.
      </p>
      <button className="text-button" onClick={onCancel}>
        Cancel analysis
      </button>
    </section>
  );
}
