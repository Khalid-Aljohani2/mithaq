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
    TEXT_GOV_WITHIN_LIMITS,
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

# ---------------------------------------------------------------------------
# (f) government PCR inside every Article 67 cap
# ---------------------------------------------------------------------------
_GOV_WITHIN_LIMITS = {
    Stage.INTAKE: _intake(
        confidence=Decimal("0.95"),
        requester_name_ar="م. فهد القحطاني",
        requested_change_ar=(
            "زيادة عدد خوادم بيئة التشغيل باثني عشر خادمًا من نفس الطراز "
            "المعتمد وبسعر الوحدة المتعاقد عليه."
        ),
        impact_type=ImpactType.COST,
        quoted_phrase_ar="نرجو زيادة عدد خوادم بيئة التشغيل باثني عشر خادمًا إضافيًا",
    ),
    Stage.SCOPE_ANALYSIS: _scope(
        confidence=Decimal("0.92"),
        in_scope=False,
        kind=ChangeKind.PCR,
        matched_line_ids=("ITM-05",),
        quantity_delta=Decimal("12"),
        quoted_phrase_ar="من نفس الطراز المعتمد في العقد A-2400 وبسعر الوحدة المتعاقد عليه",
        reasoning_ar=(
            "البند ITM-05 قائم في جدول الكميات، والطلب يزيد الكمية "
            "عليه بنفس المواصفة وسعر الوحدة، فهو زيادة في بند قائم وليس بندًا جديدًا."
        ),
    ),
    Stage.TECHNICAL_ASSESSMENT: _technical(
        confidence=Decimal("0.94"),
        changes_approved_product=False,
        affected_line_ids=("ITM-05",),
        reasoning_ar=(
            "الطلب يورّد نفس الطراز المعتمد A-2400، فلا يوجد تغيير "
            "لمنتج معتمد ولا مخالفة لقيد تعاقدي."
        ),
    ),
    Stage.RISK_COMPLIANCE: _risk(
        confidence=Decimal("0.9"),
        delivery_risk_ar="توريد الخوادم ضمن مدة العقد دون تمديد.",
        operational_risk_ar="يتطلب تهيئة مساحة إضافية في مركز البيانات.",
        commercial_risk_ar="الزيادة بسعر الوحدة المتعاقد عليه دون انحراف.",
        compliance_risk_ar="الزيادة ضمن حدود المادة السابعة والستين وحدود السياسة الداخلية.",
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
    text_fingerprint(TEXT_GOV_WITHIN_LIMITS): _GOV_WITHIN_LIMITS,
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
        "CANNOT_PRICE": "تعذّر تسعير الطلب من بيانات العقد، ويلزم توضيح من مقدّم الطلب.",
        "NEW_ITEM_RATE_HUMAN_ENTERED": "البند جديد ولا يوجد سعر تعاقدي مقابل، والسعر مُدخل بشريًا.",
    }
    headlines_en = {
        "CLOSE_IN_SCOPE": (
            "The request is covered by the existing contract and is recommended for"
            " closure as in scope."
        ),
        "APPROVE": "The request is recommended for approval once the approval chain completes.",
        "REJECT": "The request is recommended for rejection: it breaches a legal limit that"
        " cannot be exceeded.",
        "REQUEST_REVISION": "The request is recommended for return so the gaps can be completed"
        " before approval.",
    }
    reasons_en = {
        "IN_SCOPE": "The request is covered by existing lines in the bill of quantities.",
        "WITHIN_ALL_LIMITS": "The financial impact is within the policy and legal limits.",
        "POLICY_EXCEPTION_REQUIRED": (
            "The cumulative increase exceeds the internal policy limit and needs an exception."
        ),
        "LEGAL_CAP_EXCEEDED": "The increase exceeds the legal limit in Article 67.",
        "TECHNICAL_APPROVAL_REQUIRED": (
            "The request changes an approved product and needs technical approval."
        ),
        "UNIT_RATE_DEVIATION": (
            "The proposed unit rate deviates from the contract rate by more than the allowed limit."
        ),
        "DOCUMENTS_MISSING": "The required documents are incomplete.",
        "CANNOT_PRICE": (
            "The request could not be priced from the contract data; the requester must clarify it."
        ),
        "NEW_ITEM_RATE_HUMAN_ENTERED": (
            "The item is new with no contract rate to match, so its rate was entered by a person."
        ),
    }
    approve = recommendation == "APPROVE"
    return NarrativeOutput(
        provider=PROVIDER_NAME,
        recorded=True,
        confidence=Decimal("0.9"),
        summary_ar=headlines.get(recommendation, "تمت دراسة الطلب."),
        reasons_ar=tuple(reasons[code] for code in reason_codes if code in reasons),
        next_actions_ar=(
            ("رفع الطلب إلى أصحاب الصلاحية حسب سلسلة الاعتماد.",)
            if approve
            else ("إبلاغ مقدم الطلب بالنتيجة والأسباب.",)
        ),
        summary_en=headlines_en.get(recommendation, "The request has been reviewed."),
        reasons_en=tuple(reasons_en[code] for code in reason_codes if code in reasons_en),
        next_actions_en=(
            ("Send the request to the approvers, following the approval chain.",)
            if approve
            else ("Tell the requester the outcome and the reasons.",)
        ),
    )


#: English wording of each recorded request's change, for the VO scope
#: paragraph. Written by hand from the Arabic; it adds no figure the Arabic
#: does not state.
_REQUEST_EN: dict[str, str] = {
    TEXT_IN_SCOPE: (
        "three training workshops for the entity's staff on using the system during"
        " the pilot operation, one training day per workshop."
    ),
    TEXT_PCR_SMALL: (
        "one additional integration point with the electronic correspondence system,"
        " at the contracted unit rate, the contract's four integration points being"
        " fully used."
    ),
    TEXT_SUBSTITUTION: (
        "replacing the approved A-2400 servers, which the supplier has discontinued,"
        " with the same number of B-3100 servers of higher specification, at a unit"
        " rate of 56,000 SAR instead of 45,000 SAR, new and with a five-year warranty."
    ),
    TEXT_PCR_OVER_POLICY: (
        "an advanced reporting and analytics module outside the contract scope,"
        " with interactive dashboards, scheduled reports and a link to the data"
        " warehouse, offered by the contractor at 1,008,000 SAR over forty-five days."
    ),
    TEXT_NCR: (
        "reducing the training days from forty to twenty-five, and reducing the line"
        " value by the equivalent of the cancelled days."
    ),
    TEXT_GOV_WITHIN_LIMITS: (
        "twelve additional production servers of the contract's approved A-2400"
        " model at the contracted unit rate, because expected beneficiary numbers"
        " exceed the tender estimates, with no extension to the contract term."
    ),
}
_REQUEST_FALLBACK_EN = "the change described in the original Arabic request."


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
        scope_en=(
            "This variation order covers: "
            f"{_REQUEST_EN.get(requested_change_ar, _REQUEST_FALLBACK_EN)}"
            " It is carried out under the lines cited below, without prejudice to the other"
            " terms of the contract."
        ),
    )
