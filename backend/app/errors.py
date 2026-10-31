"""Turn Pydantic request errors into the contract intake's 422 shape.

The intake form needs one shape for every refusal, whether a field failed
type parsing (here) or a business rule (``app.services.contracts``):
``{code: "CONTRACT_INVALID", message, problems: [{field, code, message_ar,
message_en}]}``. Other routes keep FastAPI's default body.
"""

from collections.abc import Sequence
from typing import Any

from app.schemas.contracts import ContractInvalidDetail, ContractProblem

CONTRACT_INTAKE_PATHS = frozenset({"/api/contracts", "/api/contracts/draft"})

#: Pydantic error type -> (our code, Arabic message).
_CODES: dict[str, tuple[str, str]] = {
    "missing": ("REQUIRED", "هذا الحقل مطلوب."),
    "extra_forbidden": ("UNKNOWN_FIELD", "حقل غير معروف."),
    "enum": ("INVALID_CHOICE", "قيمة غير مسموحة."),
    "decimal_parsing": ("NOT_A_NUMBER", "القيمة ليست رقمًا صالحًا."),
    "decimal_type": ("NOT_A_NUMBER", "القيمة ليست رقمًا صالحًا."),
    "finite_number": ("NOT_A_NUMBER", "القيمة ليست رقمًا صالحًا."),
    "date_from_datetime_parsing": ("INVALID_DATE", "تاريخ غير صالح."),
    "date_parsing": ("INVALID_DATE", "تاريخ غير صالح."),
    "date_type": ("INVALID_DATE", "تاريخ غير صالح."),
    "string_too_long": ("TOO_LONG", "النص أطول من المسموح."),
    "too_long": ("TOO_LONG", "عدد العناصر أكبر من المسموح."),
    "string_type": ("INVALID_VALUE", "قيمة غير صالحة."),
    "list_type": ("INVALID_VALUE", "قيمة غير صالحة."),
}


def field_path(loc: Sequence[Any]) -> str:
    """``("body", "breakdown", 2, "quantity")`` -> ``breakdown[2].quantity``."""
    parts = list(loc[1:] if loc and loc[0] == "body" else loc)
    out = ""
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out or "body"


def contract_invalid_detail(errors: Sequence[Any]) -> dict[str, Any]:
    """Build the ``detail`` object from ``RequestValidationError.errors()``."""
    problems = []
    for error in errors:
        code, message_ar = _CODES.get(str(error.get("type")), ("INVALID_VALUE", "قيمة غير صالحة."))
        problems.append(
            ContractProblem(
                field=field_path(error.get("loc", ())),
                code=code,
                message_ar=message_ar,
                message_en=str(error.get("msg", "Invalid value")),
            )
        )
    return ContractInvalidDetail(
        message="the request did not match the expected fields", problems=problems
    ).model_dump()
