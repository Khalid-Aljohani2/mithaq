/**
 * Actor glyphs (FR-15) and the approval seal.
 *
 * Code computes (a calculator), AI reads (a scanning lens), a human signs
 * (a pen nib). Each sits in a round disc so the three are told apart by shape
 * as well as by icon.
 */

import { Calculator, PenLine, ScanSearch } from "lucide-react";

import type { ActorType } from "@/lib/api";
import { ACTOR_LABEL } from "@/lib/labels";
import { getDict } from "@/lib/prefs";
import { cn } from "@/lib/utils";

export function ActorGlyph({
  actor,
  className,
}: {
  actor: ActorType;
  className?: string;
}) {
  const Icon = actor === "CODE" ? Calculator : actor === "AI" ? ScanSearch : PenLine;
  return (
    <span
      title={ACTOR_LABEL[actor]}
      className={cn(
        "inline-flex size-6 shrink-0 items-center justify-center rounded-full border",
        actor === "AI" && "border-ink bg-ink text-paper",
        actor === "CODE" && "border-rule-strong bg-sheet text-ink",
        actor === "HUMAN" && "border-seal bg-seal-wash text-seal",
        className,
      )}
    >
      <Icon aria-hidden className="size-3.5" strokeWidth={2} />
      <span className="sr-only">{ACTOR_LABEL[actor]}</span>
    </span>
  );
}

/**
 * The approval seal: a double ring with the word and the date set around it,
 * stamped at a slight angle. Drawn in SVG so it stays crisp at any size and
 * takes its colour from the seal token in both themes.
 */
export function Seal({
  date,
  label = getDict().common.approvedSeal,
  className,
}: {
  date: string;
  label?: string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label={`${label}${getDict().common.listSep}${date}`}
      className={cn("text-seal", className)}
      shapeRendering="geometricPrecision"
      textRendering="geometricPrecision"
    >
      <defs>
        <path id="seal-arc-top" d="M 20 60 A 40 40 0 0 1 100 60" />
        <path id="seal-arc-bottom" d="M 16 60 A 44 44 0 0 0 104 60" />
      </defs>
      <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="60" cy="60" r="50" fill="none" stroke="currentColor" strokeWidth="1" />
      <circle cx="60" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="1" />
      <text
        fill="currentColor"
        fontSize="11"
        fontFamily="var(--font-naskh)"
        fontWeight="600"
      >
        <textPath href="#seal-arc-top" startOffset="50%" textAnchor="middle">
          MithaqAi
        </textPath>
      </text>
      <text fill="currentColor" fontSize="9.5" fontFamily="var(--font-ui)">
        <textPath href="#seal-arc-bottom" startOffset="50%" textAnchor="middle">
          {date}
        </textPath>
      </text>
      <text
        x="60"
        y="67"
        textAnchor="middle"
        fill="currentColor"
        fontSize="19"
        fontWeight="700"
        fontFamily="var(--font-naskh)"
      >
        {label}
      </text>
    </svg>
  );
}
