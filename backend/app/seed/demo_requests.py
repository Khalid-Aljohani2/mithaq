"""The six demo change requests, in Arabic.

The text constants here are the single source of truth. The scripted provider
keys its recordings off ``text_fingerprint`` of these same strings, computed at
import, so a recording can never drift out of sync with the text it describes.

All names and companies are fictional (NFR-08).

===  ==========================================================  ==============
id   what it demonstrates                                        contract
===  ==========================================================  ==============
a    already covered by the breakdown - closes as in scope       private
b    a PCR within every limit - Project Manager approval only    private
c    substitution of an approved product - adds technical        private
d    a PCR reaching exactly 21% - CEO exception added            private
e    an NCR reducing a quantity                                  private
d-g  the same 21% request, blocked by Article 67                 government
===  ==========================================================  ==============
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.change_request import ChangeRequest, text_fingerprint
from app.domain.enums import Party
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID, PRIVATE_CONTRACT_ID

# ---------------------------------------------------------------------------
# (a) Already covered by breakdown line ITM-07 (40 training days contracted).
# ---------------------------------------------------------------------------
TEXT_IN_SCOPE = (
    "السلام عليكم،\n"
    "نرجو تنفيذ ثلاث ورش تدريبية لمنسوبي الإدارة على استخدام النظام "
    "خلال مرحلة التشغيل التجريبي، بواقع يوم تدريبي لكل ورشة.\n"
    "ولكم تحياتنا."
)

# ---------------------------------------------------------------------------
# (b) PCR: one extra integration point on ITM-04 at the contract rate.
#     135,000 SAR = 2.8125% of the contract. Under every threshold.
# ---------------------------------------------------------------------------
TEXT_PCR_SMALL = (
    "نفيدكم بالحاجة إلى إضافة نقطة تكامل واحدة مع نظام المراسلات الإلكترونية، "
    "علمًا بأن العقد يشمل أربع نقاط تكامل وهي مستنفدة بالكامل.\n"
    "نأمل اعتماد النقطة الإضافية وفق سعر الوحدة المتعاقد عليه."
)

# ---------------------------------------------------------------------------
# (c) Substitution: the approved A-2400 servers replaced by another model at a
#     higher rate. 56,000 vs the contract rate of 45,000 is a 24.44% deviation,
#     above the 20% policy threshold, so it is flagged.
# ---------------------------------------------------------------------------
TEXT_SUBSTITUTION = (
    "نظرًا لتوقف المورّد عن إنتاج الخوادم من طراز A-2400 المعتمد في العقد، "
    "نقترح استبدالها بخوادم من طراز B-3100 بنفس العدد وبمواصفات أعلى، "
    "بسعر وحدة قدره 56,000 ريال بدلًا من 45,000 ريال.\n"
    "الخوادم المقترحة جديدة وبضمان خمس سنوات."
)

# ---------------------------------------------------------------------------
# (d) PCR with a human-entered lump sum of 1,008,000 SAR.
#     Exactly 21% of 4,800,000, so it clears the policy 20% cap by 1 point.
#     No matching breakdown line, so Q1's default applies: the rate is
#     human-entered and the request is flagged.
# ---------------------------------------------------------------------------
TEXT_PCR_OVER_POLICY = (
    "نطلب إضافة وحدة تقارير وتحليلات متقدمة لم تكن ضمن نطاق العقد، "
    "تشمل لوحات مؤشرات تفاعلية وتقارير مجدولة وربطًا بمستودع البيانات.\n"
    "قيمة العرض المقدم من المقاول 1,008,000 ريال، ومدة التنفيذ خمسة وأربعون يومًا."
)

# ---------------------------------------------------------------------------
# (e) NCR: training days on ITM-07 cut from 40 to 25.
#     15 days x 7,500 = 112,500 SAR removed.
# ---------------------------------------------------------------------------
TEXT_NCR = (
    "بناءً على انخفاض عدد المستفيدين، نرغب في تخفيض أيام التدريب "
    "من أربعين يومًا تدريبيًا إلى خمسة وعشرين يومًا تدريبيًا، "
    "وتخفيض قيمة البند بما يعادل الأيام الملغاة."
)


class DemoRequest:
    """A seeded change request plus the facts tests assert against."""

    __slots__ = (
        "amount",
        "attachments",
        "body_ar",
        "contract_id",
        "days",
        "id",
        "label",
        "requester",
        "unit_rate",
    )

    def __init__(
        self,
        cr_id: str,
        contract_id: str,
        label: str,
        body_ar: str,
        requester: str,
        attachments: tuple[str, ...],
        amount: Decimal | None = None,
        unit_rate: Decimal | None = None,
        days: int | None = None,
    ) -> None:
        self.id = cr_id
        self.contract_id = contract_id
        self.label = label
        self.body_ar = body_ar
        self.requester = requester
        self.attachments = attachments
        self.amount = amount
        self.unit_rate = unit_rate
        self.days = days

    @property
    def fingerprint(self) -> str:
        return text_fingerprint(self.body_ar)


#: Documents the demo requests arrive with. The stage 2 checklist is keyed off
#: the impact type that stage 1 extracts, so these are chosen to be complete.
_COST_DOCS = ("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة")
_COST_AND_TIME_DOCS = (*_COST_DOCS, "برنامج زمني محدّث")

DEMO_REQUESTS: tuple[DemoRequest, ...] = (
    DemoRequest(
        "CR-A-INSCOPE",
        PRIVATE_CONTRACT_ID,
        "already covered by the breakdown",
        TEXT_IN_SCOPE,
        "م. سارة العتيبي",
        ("طلب تغيير رسمي",),
    ),
    DemoRequest(
        "CR-B-PCR",
        PRIVATE_CONTRACT_ID,
        "PCR within every limit",
        TEXT_PCR_SMALL,
        "م. فهد القحطاني",
        _COST_DOCS,
    ),
    DemoRequest(
        "CR-C-SUBSTITUTION",
        PRIVATE_CONTRACT_ID,
        "substitution of an approved product",
        TEXT_SUBSTITUTION,
        "م. نورة الدوسري",
        (*_COST_DOCS, "مواصفات المنتج البديل"),
        unit_rate=Decimal("56000"),
    ),
    DemoRequest(
        "CR-D-POLICY",
        PRIVATE_CONTRACT_ID,
        "PCR reaching 21% - CEO exception",
        TEXT_PCR_OVER_POLICY,
        "م. فهد القحطاني",
        _COST_AND_TIME_DOCS,
        amount=Decimal("1008000"),
        days=45,
    ),
    DemoRequest(
        "CR-E-NCR",
        PRIVATE_CONTRACT_ID,
        "NCR reducing a quantity",
        TEXT_NCR,
        "م. سارة العتيبي",
        _COST_DOCS,
    ),
    DemoRequest(
        "CR-D-GOV",
        GOVERNMENT_CONTRACT_ID,
        "the same 21% request, blocked by Article 67",
        TEXT_PCR_OVER_POLICY,
        "م. فهد القحطاني",
        _COST_AND_TIME_DOCS,
        amount=Decimal("1008000"),
        days=45,
    ),
)

#: The lump sum quoted in request (d). Exactly 21% of the contract value.
POLICY_BREACH_VALUE = Decimal("1008000")
#: The substitute unit rate quoted in request (c).
SUBSTITUTE_UNIT_RATE = Decimal("56000")

_SEEDED_AT = datetime(2027, 2, 1, 8, 0, tzinfo=UTC)


def build_demo_requests() -> tuple[ChangeRequest, ...]:
    """Build the seeded change requests in their initial RECEIVED state."""
    return tuple(
        ChangeRequest(
            id=demo.id,
            contract_id=demo.contract_id,
            requester_name=demo.requester,
            requester_party=Party.CONTRACTOR,
            submitted_at=_SEEDED_AT,
            body_ar=demo.body_ar,
            attachments=demo.attachments,
            human_entered_amount=demo.amount,
            human_entered_unit_rate=demo.unit_rate,
            human_entered_days=demo.days,
        )
        for demo in DEMO_REQUESTS
    )
