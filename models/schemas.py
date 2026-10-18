from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Criterion:
    criterion_id: int
    name: str
    description: str
    weight: float
    max_score: float
    is_active: bool = True


@dataclass
class ScoreEntry:
    criterion_id: int
    name: str
    weight: float
    score: float
    max_score: float
    justification: str = ""
    evidence: str = ""


@dataclass
class ValidatedScorecard:
    supplier_name: str
    criteria: list[ScoreEntry]
    risks: list[str] = field(default_factory=list)
    overall_summary: str = ""
    warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SupplierInput:
    supplier_name: str
    submission_date: str
    experience_rating: float
    filename: str
    pdf_bytes: bytes


@dataclass
class RankingResult:
    leaderboard: list[dict[str, Any]]
    suppliers: list[dict[str, Any]]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    tie_break_notes: list[str] = field(default_factory=list)


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value
