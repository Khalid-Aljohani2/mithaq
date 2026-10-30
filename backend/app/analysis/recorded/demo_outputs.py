"""Recorded AI outputs for the seeded demo requests (FR-19).

Keyed by ``text_fingerprint`` of the request text, computed at import from the
same constants the seed uses. There is no JSON file to regenerate and no hash
to paste, so a recording cannot drift away from the text it describes.

Every output carries ``recorded=True``. The UI must label these as recorded
rather than presenting them as live analysis.
"""

from decimal import Decimal

from app.analysis.schemas import (
    IntakeOutput,
    NarrativeOutput,
    RiskOutput,
    ScopeOutput,
    TechnicalOutput,
    VODraftOutput,
)
from app.domain.change_request import text_fingerprint
from app.domain.enums import ChangeKind, ImpactType, Stage
from app.seed.demo_requests import (
    TEXT_IN_SCOPE,
    TEXT_NCR,
    TEXT_PCR_OVER_POLICY,
    TEXT_PCR_SMALL,
    TEXT_SUBSTITUTION,
)

PROVIDER_NAME = "scripted"


def _intake(**kwargs: object) -> IntakeOutput:
    return IntakeOutput(provider=PROVIDER_NAME, recorded=True, **kwargs)  # type: ignore[arg-type]


def _scope(**kwargs: object) -> ScopeOutput:
    return ScopeOutput(provider=PROVIDER_NAME, recorded=True, **kwargs)  # type: ignore[arg-type]


def _technical(**kwargs: object) -> TechnicalOutput:
    return TechnicalOutput(provider=PROVIDER_NAME, recorded=True, **kwargs)  # type: ignore[arg-type]


def _risk(**kwargs: object) -> RiskOutput:
    return RiskOutput(provider=PROVIDER_NAME, recorded=True, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# (a) in scope
# ---------------------------------------------------------------------------
_IN_SCOPE = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.93"),
        requester_name_ar="م. سارة العتيبي",
        requested_change_ar="تنفيذ ثلاث ورش تدريبية لمنسوبي الإدارة خلال التشغيل التجريبي.",
        impact_type=ImpactType.NONE,
        quoted_phrase_ar="نرجو تنفيذ ثلاث ورش تدريبية لمنسوبي الإدارة",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.91"),
        in_scope=True,
        kind=ChangeKind.IN_SCOPE,
        matched_line_ids=("ITM-07",),
        quoted_phrase_ar="بواقع يوم تدريبي لكل ورشة",
        reasoning_ar=(
            "البند ITM-07 يغطي أربعين يومًا تدريبيًا، والورش الثلاث المطلوبة "
            "تعادل ثلاثة أيام تدريبية ضمن الكمية المتعاقد عليها، "
            "فالطلب داخل النطاق ولا يُعد تغييرًا."
        ),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.95"),
        changes_approved_product=False,
        reasoning_ar="لا يمس الطلب أي منتج أو مواصفة معتمدة.",
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.9"),
        delivery_risk_ar="لا يوجد أثر على الجدول الزمني.",
        operational_risk_ar="ينفذ ضمن الأيام التدريبية المتعاقد عليها.",
        commercial_risk_ar="لا يوجد أثر مالي.",
        compliance_risk_ar="لا ينطبق حد نظامي لأن الطلب داخل النطاق.",
        overall_risk_level="LOW",
    ),
}

# ---------------------------------------------------------------------------
# (b) PCR within every limit
# ---------------------------------------------------------------------------
_PCR_SMALL = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.94"),
        requester_name_ar="م. فهد القحطاني",
        requested_change_ar="إضافة نقطة تكامل واحدة مع نظام المراسلات الإلكترونية.",
        impact_type=ImpactType.COST,
        quoted_phrase_ar="الحاجة إلى إضافة نقطة تكامل واحدة مع نظام المراسلات الإلكترونية",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.9"),
        in_scope=False,
        kind=ChangeKind.PCR,
        matched_line_ids=("ITM-04",),
        quantity_delta=Decimal("1"),
        quoted_phrase_ar="العقد يشمل أربع نقاط تكامل وهي مستنفدة بالكامل",
        reasoning_ar=(
            "الكمية المتعاقد عليها في البند ITM-04 أربع نقاط تكامل ومستنفدة، "
            "والطلب يضيف نقطة خامسة، فهو زيادة في بند قائم."
        ),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.92"),
        changes_approved_product=False,
        affected_line_ids=("ITM-04",),
        reasoning_ar="زيادة كمية ضمن نفس المواصفة، دون تغيير لمنتج معتمد.",
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.88"),
        delivery_risk_ar="أثر محدود على الجدول الزمني.",
        operational_risk_ar="يتطلب تنسيقًا مع مالك نظام المراسلات.",
        commercial_risk_ar="الزيادة ضمن الحدود المسموح بها.",
        compliance_risk_ar="لا توجد مخالفة للسياسة أو النظام.",
        overall_risk_level="LOW",
    ),
}

# ---------------------------------------------------------------------------
# (c) substitution of an approved product
# ---------------------------------------------------------------------------
_SUBSTITUTION = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.92"),
        requester_name_ar="م. نورة الدوسري",
        requested_change_ar=("استبدال الخوادم المعتمدة طراز A-2400 بخوادم طراز B-3100 بنفس العدد."),
        impact_type=ImpactType.COST,
        quoted_phrase_ar="نقترح استبدالها بخوادم من طراز B-3100 بنفس العدد",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.89"),
        in_scope=False,
        kind=ChangeKind.SUBSTITUTION,
        matched_line_ids=("ITM-05",),
        quantity_delta=Decimal("12"),
        substitute_product_ar="خوادم من الفئة المؤسسية طراز B-3100",
        quoted_phrase_ar="توقف المورّد عن إنتاج الخوادم من طراز A-2400 المعتمد في العقد",
        reasoning_ar=(
            "الطلب يستبدل المنتج المعتمد في البند ITM-05 بمنتج آخر بنفس الكمية، "
            "فهو إحلال يُحتسب تخفيضًا لما يُزال وزيادةً لما يُضاف."
        ),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.9"),
        changes_approved_product=True,
        affected_line_ids=("ITM-05",),
        reasoning_ar=(
            "المنتج المعتمد في العقد هو طراز A-2400، والمقترح طراز مختلف، "
            "ما يستوجب اعتمادًا فنيًا. الخوادم المقترحة جديدة وبضمان خمس سنوات، "
            "فلا تتعارض مع قيدي منع الخوادم المجددة والضمان."
        ),
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.86"),
        delivery_risk_ar="توقف إنتاج الطراز المعتمد يهدد الجدول إن لم يُعتمد البديل.",
        operational_risk_ar="يتطلب إعادة اختبار التوافق مع بيئة التشغيل.",
        commercial_risk_ar="سعر الوحدة المقترح أعلى من سعر العقد ويستوجب مراجعة.",
        compliance_risk_ar="البديل مطابق للقيود المنصوص عليها في البند.",
        overall_risk_level="MEDIUM",
    ),
}

# ---------------------------------------------------------------------------
# (d) PCR reaching 21%
# ---------------------------------------------------------------------------
_PCR_OVER_POLICY = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.91"),
        requester_name_ar="م. فهد القحطاني",
        requested_change_ar=(
            "إضافة وحدة تقارير وتحليلات متقدمة خارج نطاق العقد بقيمة 1,008,000 ريال "
            "ومدة خمسة وأربعين يومًا."
        ),
        impact_type=ImpactType.BOTH,
        quoted_phrase_ar="نطلب إضافة وحدة تقارير وتحليلات متقدمة لم تكن ضمن نطاق العقد",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.87"),
        in_scope=False,
        kind=ChangeKind.PCR,
        matched_line_ids=(),
        quoted_phrase_ar="لم تكن ضمن نطاق العقد",
        reasoning_ar=(
            "لا يوجد بند في جدول الكميات يغطي وحدة التقارير والتحليلات المتقدمة، "
            "فالطلب بند جديد لا زيادة على بند قائم."
        ),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.88"),
        changes_approved_product=False,
        reasoning_ar="بند جديد لا يغيّر منتجًا معتمدًا قائمًا.",
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.84"),
        delivery_risk_ar="خمسة وأربعون يومًا إضافية تؤثر على تاريخ التسليم النهائي.",
        operational_risk_ar="يتطلب ربطًا بمستودع البيانات وموارد إضافية.",
        commercial_risk_ar="قيمة مرتفعة تتجاوز حد السياسة الداخلية.",
        compliance_risk_ar="يستوجب مراجعة الحدود التراكمية قبل الاعتماد.",
        overall_risk_level="HIGH",
    ),
}

# ---------------------------------------------------------------------------
# (e) NCR
# ---------------------------------------------------------------------------
_NCR = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.93"),
        requester_name_ar="م. سارة العتيبي",
        requested_change_ar="تخفيض أيام التدريب من أربعين يومًا إلى خمسة وعشرين يومًا.",
        impact_type=ImpactType.COST,
        quoted_phrase_ar="تخفيض أيام التدريب من أربعين يومًا تدريبيًا إلى خمسة وعشرين يومًا تدريبيًا",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.92"),
        in_scope=False,
        kind=ChangeKind.NCR,
        matched_line_ids=("ITM-07",),
        quantity_delta=Decimal("15"),
        quoted_phrase_ar="بناءً على انخفاض عدد المستفيدين",
        reasoning_ar=("الطلب يخفّض كمية البند ITM-07 بخمسة عشر يومًا تدريبيًا، فهو تخفيض لبند قائم."),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.94"),
        changes_approved_product=False,
        affected_line_ids=("ITM-07",),
        reasoning_ar="تخفيض كمية دون أثر على منتج أو مواصفة معتمدة.",
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.89"),
        delivery_risk_ar="لا يوجد أثر سلبي على الجدول.",
        operational_risk_ar="قد يقلل جاهزية المستخدمين عند التشغيل.",
        commercial_risk_ar="تخفيض في قيمة العقد لصالح الجهة.",
        compliance_risk_ar="التخفيض ضمن الحدود المسموح بها.",
        overall_risk_level="LOW",
    ),
}


#: fingerprint -> stage -> recorded output
RECORDINGS: dict[str, dict[Stage, object]] = {
    text_fingerprint(TEXT_IN_SCOPE): _IN_SCOPE,
    text_fingerprint(TEXT_PCR_SMALL): _PCR_SMALL,
    text_fingerprint(TEXT_SUBSTITUTION): _SUBSTITUTION,
    text_fingerprint(TEXT_PCR_OVER_POLICY): _PCR_OVER_POLICY,
    text_fingerprint(TEXT_NCR): _NCR,
}


def narrative_for(recommendation: str, reason_codes: tuple[str, ...]) -> NarrativeOutput:
    """Recorded prose for stage 7.

    Keyed on the decision rather than the request, because by this point code
    has already decided and the prose only has to describe that decision. This
    is why a missing narrative cannot change an outcome.
    """
    headlines = {
        "CLOSE_IN_SCOPE": "الطلب مغطى بالعقد الحالي ويوصى بإغلاقه كطلب داخل النطاق.",
        "APPROVE": "يوصى باعتماد الطلب بعد استكمال سلسلة الاعتماد.",
        "REJECT": "يوصى برفض الطلب لتعارضه مع حد نظامي لا يجوز تجاوزه.",
        "REQUEST_REVISION": "يوصى بإعادة الطلب لاستكمال النواقص قبل الاعتماد.",
    }
    reasons = {
        "IN_SCOPE": "الطلب مغطى ببنود قائمة في جدول الكميات.",
        "WITHIN_ALL_LIMITS": "الأثر المالي ضمن حدود السياسة والنظام.",
        "POLICY_EXCEPTION_REQUIRED": (
            "الزيادة التراكمية تتجاوز حد السياسة الداخلية وتستوجب استثناءً."
        ),
        "LEGAL_CAP_EXCEEDED": "الزيادة تتجاوز الحد النظامي في المادة السابعة والستين.",
        "TECHNICAL_APPROVAL_REQUIRED": "الطلب يغيّر منتجًا معتمدًا ويستوجب اعتمادًا فنيًا.",
        "UNIT_RATE_DEVIATION": "سعر الوحدة المقترح ينحرف عن سعر العقد بما يتجاوز الحد المسموح.",
        "DOCUMENTS_MISSING": "المستندات المطلوبة غير مكتملة.",
        "NEW_ITEM_RATE_HUMAN_ENTERED": "البند جديد ولا يوجد سعر تعاقدي مقابل، والسعر مُدخل بشريًا.",
    }
    return NarrativeOutput(
        provider=PROVIDER_NAME,
        recorded=True,
        confidence=Decimal("0.9"),
        summary_ar=headlines.get(recommendation, "تمت دراسة الطلب."),
        reasons_ar=tuple(reasons[code] for code in reason_codes if code in reasons),
        next_actions_ar=(
            ("رفع الطلب إلى أصحاب الصلاحية حسب سلسلة الاعتماد.",)
            if recommendation == "APPROVE"
            else ("إبلاغ مقدم الطلب بالنتيجة والأسباب.",)
        ),
    )


def vo_scope_for(requested_change_ar: str) -> VODraftOutput:
    """Recorded scope prose for a variation order (stage 9)."""
    return VODraftOutput(
        provider=PROVIDER_NAME,
        recorded=True,
        confidence=Decimal("0.9"),
        scope_ar=(
            f"يشمل أمر التغيير هذا: {requested_change_ar} "
            "وذلك وفقًا للبنود المشار إليها أدناه وبما لا يخل بباقي أحكام العقد."
        ),
    )
