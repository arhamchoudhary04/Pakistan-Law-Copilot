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
      className="mx-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-md bg-indigo-500/20 px-1 align-baseline text-[11px] font-semibold text-indigo-300 ring-1 ring-inset ring-indigo-400/40 transition hover:bg-indigo-500/40 hover:text-indigo-200"
    >
      {marker}
    </button>
  );
}
