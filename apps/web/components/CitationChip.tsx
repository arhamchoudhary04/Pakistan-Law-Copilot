"use client";

/** An inline footnote-style citation marker, rendered as a superscript. */
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
      className="relative -top-[0.4em] mx-[1px] text-[0.68em] font-semibold text-accent underline decoration-accent/30 decoration-1 underline-offset-2 transition hover:decoration-accent"
    >
      {marker}
    </button>
  );
}
