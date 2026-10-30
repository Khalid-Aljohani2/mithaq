"""Saying how long something has been waiting, in both languages.

Only presentation lives here. The decision about whether to remind at all is
made from the configured delay, in code, against unrounded timestamps; this
module turns the result into a phrase a person can read.

Arabic is not English with different words. It counts in singular, dual and
plural, and the plural form changes again above ten, so ``f"{n} ساعة"`` is
wrong for almost every value of ``n``. An Arabic-first product that gets this
wrong reads like a machine translation of an English product, which is exactly
what it must not be.
"""

#: 3 to 10 take the "few" plural; 11 and above return to the singular noun.
_FEW_MAX = 10


def waited_phrase(hours: int) -> tuple[str, str]:
    """``(arabic, english)`` for a wait of ``hours`` whole hours.

    Zero is a real answer, not a missing one: with the reminder delay set to 0
    for a demo, a notice fires within the first hour and "0 hours ago" is both
    wrong and obviously machine-written. It reads as "less than an hour".
    """
    if hours <= 0:
        return "أقل من ساعة", "less than an hour"
    if hours == 1:
        return "ساعة", "1 hour"
    if hours == 2:  # noqa: PLR2004 - Arabic has a dual form, and this is it
        return "ساعتين", "2 hours"
    if hours <= _FEW_MAX:
        return f"{hours} ساعات", f"{hours} hours"
    return f"{hours} ساعة", f"{hours} hours"
