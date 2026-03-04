from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardedAnswer:
    conclusion: str
    law_basis: str
    notice: str
    quotation: str
    era: str
    confidence: float


GUARD_RULES = [
    "推論禁止",
    "解釈生成禁止",
    "原文引用必須",
]


def format_guarded_answer(answer: GuardedAnswer) -> str:
    return (
        "結論\n"
        f"{answer.conclusion}\n\n"
        "根拠法令\n"
        f"{answer.law_basis}\n\n"
        "通知\n"
        f"{answer.notice}\n\n"
        "原文引用\n"
        f"{answer.quotation}\n\n"
        "年代\n"
        f"{answer.era}\n\n"
        "信頼度\n"
        f"{answer.confidence:.2f}\n"
    )
