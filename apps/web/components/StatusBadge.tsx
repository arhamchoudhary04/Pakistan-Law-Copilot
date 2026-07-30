import type { AnswerStatus } from "@/lib/types";

const LABELS: Record<AnswerStatus, string> = {
  grounded: "Grounded",
  idk: "I don't know",
  partial: "Partial",
};

const STYLES: Record<AnswerStatus, string> = {
  grounded: "bg-grounded/12 text-grounded ring-grounded/30",
  idk: "bg-idk/12 text-idk ring-idk/30",
  partial: "bg-partial/12 text-partial ring-partial/35",
};

/** Answer-status badge: a refusal looks visibly different from a grounded answer. */
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
