"""Demo seed data.

Everything here is FICTIONAL. The entity, the contractor, the project and the
people are invented for the demo. No real government body, company or person is
named anywhere in this file (NFR-08).
"""

from datetime import date
from decimal import Decimal

from app.domain.models import Contract, ContractItem

DEMO_CONTRACT_ID = "CT-2027-0418"

#: Fictional government entity.
_ENTITY_NAME = "أمانة منطقة الواحة"
#: Fictional contractor.
_CONTRACTOR_NAME = "شركة أفق الرقمية لتقنية المعلومات"

_ITEMS: tuple[tuple[str, str, str, str], ...] = (
    ("ITM-01", "تحليل المتطلبات وتصميم معمارية النظام", "1", "450000"),
    ("ITM-02", "تطوير وحدة إدارة المستخدمين والصلاحيات", "1", "620000"),
    ("ITM-03", "تطوير وحدة سير العمل والموافقات الإلكترونية", "1", "880000"),
    ("ITM-04", "تكامل النظام مع الأنظمة الحكومية القائمة", "1", "540000"),
    ("ITM-05", "توريد وتهيئة خوادم بيئة التشغيل", "12", "45000"),
    ("ITM-06", "ترخيص قاعدة البيانات السنوي", "3", "260000"),
    ("ITM-07", "التدريب ونقل المعرفة لمنسوبي الجهة", "40", "7500"),
    ("ITM-08", "الدعم الفني والصيانة لمدة سنة", "12", "57500"),
)


def build_demo_contract() -> Contract:
    """Return the seeded demo contract.

    An IT system implementation worth 4,800,000 SAR across eight priced items.
    """
    items = tuple(
        ContractItem(
            id=item_id,
            description_ar=description,
            quantity=Decimal(quantity),
            unit_price=Decimal(unit_price),
            total=Decimal(quantity) * Decimal(unit_price),
        )
        for item_id, description, quantity, unit_price in _ITEMS
    )
    return Contract(
        id=DEMO_CONTRACT_ID,
        title_ar="مشروع تنفيذ نظام إدارة الخدمات الرقمية",
        entity_name=_ENTITY_NAME,
        contractor_name=_CONTRACTOR_NAME,
        original_value=Decimal("4800000"),
        items=items,
        start_date=date(2027, 1, 15),
        end_date=date(2028, 1, 14),
    )
