import type { AnswerStatus } from "@/lib/types";

const LABELS: Record<AnswerStatus, string> = {
  grounded: "Grounded",
  idk: "I don't know",
  partial: "Partial",
};

const STYLES: Record<AnswerStatus, string> = {
  grounded: "bg-grounded/10 text-grounded ring-grounded/30",
  idk: "bg-idk/10 text-idk ring-idk/30",
  partial: "bg-partial/10 text-partial ring-partial/40",
};

/**
 * The answer-status badge makes the trust state legible in ~2 seconds — a
 * refusal ("I don't know") looks visibly different from a grounded answer.
 */
export function StatusBadge({ status }: { status: AnswerStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABELS[status]}
    </span>
  );
}
