"""Formatting money for people to read.

Only presentation lives here. Nothing in this module takes part in a
comparison, a cap check or a stored value: those stay unrounded ``Decimal``
all the way through (NFR-01). A formatted string is an output, never an input.
"""

from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


def money(value: Decimal) -> str:
    """Group thousands with commas, dropping trailing zero halalas.

    ``1008000`` reads as ``1,008,000`` rather than ``1008000``: an approver
    glancing at a notification should not have to count digits to tell six
    figures from seven. Halalas are shown only when there are any, so the
    common whole-riyal case stays short.

    Rounding is half-up to two places, the convention for currency, and it
    happens here and nowhere else - the ledger keeps the exact value.
    """
    quantised = value.quantize(_CENTS, rounding=ROUND_HALF_UP)
    whole = quantised.to_integral_value()
    if quantised == whole:
        return f"{int(whole):,}"
    return f"{quantised:,.2f}"
