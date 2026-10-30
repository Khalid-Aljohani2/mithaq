"""Demo seed contracts.

Everything here is FICTIONAL. The entity, the company, the project and the
people are invented. No real government body, company or person is named
anywhere in this file (NFR-08).

Two contracts with the same breakdown, differing only in type:

* ``CT-2027-0418`` GOVERNMENT - the Article 67 caps apply on top of policy.
* ``CT-2027-0419`` PRIVATE - organisation policy only.

Having both is what lets the same 21% request be an escalation on one and a
hard legal block on the other.
"""

from datetime import date
from decimal import Decimal

from app.domain.enums import ContractType
from app.domain.models import BreakdownLine, Contract

GOVERNMENT_CONTRACT_ID = "CT-2027-0418"
PRIVATE_CONTRACT_ID = "CT-2027-0419"

#: Kept for callers that just want "the" demo contract.
DEMO_CONTRACT_ID = PRIVATE_CONTRACT_ID

_GOV_ENTITY = "أمانة منطقة الواحة"
_PRIVATE_CLIENT = "شركة واحة الخليج القابضة"
_CONTRACTOR = "شركة أفق الرقمية لتقنية المعلومات"

# id, description, unit, quantity, unit rate, approved product, restrictions
_BREAKDOWN: tuple[tuple[str, str, str, str, str, str | None, tuple[str, ...]], ...] = (
    (
        "ITM-01",
        "تحليل المتطلبات وتصميم معمارية النظام",
        "وثيقة",
        "1",
        "450000",
        None,
        ("تُعتمد الوثيقة من الجهة قبل بدء التطوير",),
    ),
    (
        "ITM-02",
        "تطوير وحدة إدارة المستخدمين والصلاحيات",
        "وحدة",
        "1",
        "620000",
        None,
        ("تطبيق مبدأ الصلاحية الأدنى",),
    ),
    (
        "ITM-03",
        "تطوير وحدة سير العمل والموافقات الإلكترونية",
        "وحدة",
        "1",
        "880000",
        None,
        (),
    ),
    (
        "ITM-04",
        "تكامل النظام مع الأنظمة الحكومية القائمة",
        "نقطة تكامل",
        "4",
        "135000",
        None,
        ("ألا يتجاوز زمن الاستجابة ثانيتين",),
    ),
    (
        "ITM-05",
        "توريد وتهيئة خوادم بيئة التشغيل",
        "خادم",
        "12",
        "45000",
        "خوادم من الفئة المؤسسية طراز A-2400",
        ("لا يجوز توريد خوادم مجددة أو مستعملة", "ضمان لا يقل عن ثلاث سنوات"),
    ),
    (
        "ITM-06",
        "ترخيص قاعدة البيانات السنوي",
        "ترخيص",
        "3",
        "260000",
        "قاعدة بيانات علائقية مرخّصة تجاريًا",
        ("يكون الترخيص باسم الجهة",),
    ),
    (
        "ITM-07",
        "التدريب ونقل المعرفة لمنسوبي الجهة",
        "يوم تدريبي",
        "40",
        "7500",
        None,
        (),
    ),
    (
        "ITM-08",
        "الدعم الفني والصيانة لمدة سنة",
        "شهر",
        "12",
        "57500",
        None,
        ("زمن استجابة للأعطال الحرجة لا يتجاوز أربع ساعات",),
    ),
)


def build_breakdown() -> tuple[BreakdownLine, ...]:
    """The eight priced breakdown lines, shared by both demo contracts."""
    return tuple(
        BreakdownLine(
            id=line_id,
            description_ar=description,
            unit_ar=unit,
            quantity=Decimal(quantity),
            unit_rate=Decimal(rate),
            total=Decimal(quantity) * Decimal(rate),
            approved_product_ar=product,
            restrictions_ar=restrictions,
        )
        for line_id, description, unit, quantity, rate, product, restrictions in _BREAKDOWN
    )


def _contract(contract_id: str, entity_name: str, contract_type: ContractType) -> Contract:
    return Contract(
        id=contract_id,
        title_ar="مشروع تنفيذ نظام إدارة الخدمات الرقمية",
        entity_name=entity_name,
        contractor_name=_CONTRACTOR,
        contract_type=contract_type,
        original_value=Decimal("4800000"),
        breakdown=build_breakdown(),
        start_date=date(2027, 1, 15),
        end_date=date(2028, 1, 14),
    )


def build_government_contract() -> Contract:
    """4,800,000 SAR over 365 days, with the Article 67 caps on top."""
    return _contract(GOVERNMENT_CONTRACT_ID, _GOV_ENTITY, ContractType.GOVERNMENT)


def build_private_contract() -> Contract:
    """The same project under organisation policy only."""
    return _contract(PRIVATE_CONTRACT_ID, _PRIVATE_CLIENT, ContractType.PRIVATE)


def build_demo_contracts() -> tuple[Contract, ...]:
    """Both seed contracts."""
    return (build_government_contract(), build_private_contract())


def build_demo_contract() -> Contract:
    """The private contract, which most demo requests run against."""
    return build_private_contract()
