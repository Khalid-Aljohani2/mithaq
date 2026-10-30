"""Loads organisation policy thresholds from ``policy.yaml``.

Mirrors ``app.regulations.loader``. The split matters: legal limits are
blocking and no internal role can lift them, whereas policy limits can be
escalated past by the role named in ``exception_role`` (NFR-16).
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

POLICY_PATH = Path(__file__).with_name("policy.yaml")

#: Where a number came from. Drives how it may be escalated past.
ThresholdSource = Literal["law", "organization_policy", "default"]


class PolicyThreshold(BaseModel):
    """One configured limit, carrying the source that justifies it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    source: ThresholdSource
    cap_pct: Decimal | None = None
    cap_value: Decimal | None = None
    basis: str | None = None
    blocking: bool = False
    exception_role: str | None = None
    description_en: str = ""
    description_ar: str = ""


class ReminderSetting(BaseModel):
    """A delay after which a pending item is reminded about."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    source: ThresholdSource
    value: int
    description_en: str = ""
    description_ar: str = ""


class NewItemRateBasis(BaseModel):
    """Open question Q1: how an unmatched new item's rate is justified."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    source: ThresholdSource
    value: str
    needs_decision: bool = False
    open_question: str | None = None
    description_en: str = ""


class Policy(BaseModel):
    """The whole organisation policy file."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    thresholds: dict[str, PolicyThreshold]
    reminders: dict[str, ReminderSetting]
    new_item_rate_basis: NewItemRateBasis

    @property
    def cost_increase_cap_pct(self) -> Decimal:
        cap = self.thresholds["cost_increase"].cap_pct
        assert cap is not None  # noqa: S101 - guaranteed by the config schema
        return cap

    @property
    def time_extension_cap_pct(self) -> Decimal:
        cap = self.thresholds["time_extension"].cap_pct
        assert cap is not None  # noqa: S101
        return cap

    @property
    def unit_rate_deviation_cap_pct(self) -> Decimal:
        cap = self.thresholds["unit_rate_deviation"].cap_pct
        assert cap is not None  # noqa: S101
        return cap

    @property
    def finance_approval_value(self) -> Decimal:
        cap = self.thresholds["finance_approval_value"].cap_value
        assert cap is not None  # noqa: S101
        return cap

    @property
    def policy_exception_role(self) -> str:
        role = self.thresholds["cost_increase"].exception_role
        assert role is not None  # noqa: S101
        return role

    @property
    def minimum_confidence(self) -> Decimal:
        """As a 0-1 fraction, to compare against what an AI stage reports."""
        cap = self.thresholds["minimum_confidence"].cap_pct
        assert cap is not None  # noqa: S101
        return cap / Decimal("100")

    @property
    def pending_approval_hours(self) -> int:
        return self.reminders["pending_approval_hours"].value

    @property
    def awaiting_documents_hours(self) -> int:
        return self.reminders["awaiting_documents_hours"].value


def load_policy(path: Path = POLICY_PATH) -> Policy:
    """Parse and validate the policy YAML."""
    return Policy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def get_policy() -> Policy:
    """Return the cached policy."""
    return load_policy()
