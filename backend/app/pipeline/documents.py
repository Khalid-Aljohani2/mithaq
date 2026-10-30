"""Stage 2 - document validation (FR-04). Deterministic code.

A checklist is a set comparison, so no model is involved.

The checklist is keyed on the **impact type** that stage 1 extracts, not on the
change kind: stage 3 is what classifies a request as PCR, NCR or substitution,
and it has not run yet when this stage does. Checking against a type we do not
yet know would be checking against a guess.
"""

from dataclasses import dataclass

from app.domain.enums import ImpactType

#: Required documents per impact type (FR-04).
CHECKLISTS: dict[ImpactType, tuple[str, ...]] = {
    ImpactType.NONE: ("طلب تغيير رسمي",),
    ImpactType.COST: ("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"),
    ImpactType.TIME: ("طلب تغيير رسمي", "برنامج زمني محدّث"),
    ImpactType.BOTH: (
        "طلب تغيير رسمي",
        "عرض سعر أو تحليل تكلفة",
        "برنامج زمني محدّث",
    ),
}


@dataclass(frozen=True)
class DocumentCheck:
    """The outcome of the checklist comparison."""

    impact_type: ImpactType
    required: tuple[str, ...]
    provided: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def gap_list_ar(self) -> str:
        """The structured gap list sent back to the requester (FR-04).

        Sending this is a non-commitment action the agent may take on its own:
        it asks for paperwork, it does not approve or reject anything.
        """
        if self.complete:
            return "المستندات المطلوبة مكتملة."
        items = "\n".join(f"- {name}" for name in self.missing)
        return "المستندات التالية مطلوبة لاستكمال دراسة الطلب:\n" + items

    @property
    def summary_en(self) -> str:
        if self.complete:
            return f"All {len(self.required)} required documents provided."
        return f"Missing {len(self.missing)} of {len(self.required)} required documents."


def check_documents(impact_type: ImpactType, attachments: tuple[str, ...]) -> DocumentCheck:
    """Compare what arrived against what this impact type requires."""
    required = CHECKLISTS[impact_type]
    provided = tuple(name.strip() for name in attachments if name.strip())
    provided_set = set(provided)
    return DocumentCheck(
        impact_type=impact_type,
        required=required,
        provided=provided,
        missing=tuple(name for name in required if name not in provided_set),
    )
