"use client";

/** A clickable inline [n] citation marker. */
export function CitationChip({
  marker,
  onClick,
}: {
  marker: number;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={`View source [${marker}]`}
      className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-sky-500/20 px-1 align-baseline text-[11px] font-semibold text-sky-300 ring-1 ring-sky-500/30 transition hover:bg-sky-500/40"
    >
      {marker}
    </button>
  );
}
