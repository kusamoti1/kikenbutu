from __future__ import annotations

from dataclasses import dataclass

RULES = {
    "屋外タンク貯蔵所": ["屋外タンク", "屋外貯蔵タンク"],
    "地下タンク貯蔵所": ["地下タンク"],
    "移動タンク貯蔵所": ["移動タンク", "タンクローリー"],
    "給油取扱所": ["給油取扱所", "給油所"],
    "一般取扱所": ["一般取扱所"],
    "製造所": ["製造所"],
    "屋内貯蔵所": ["屋内貯蔵所"],
    "屋外貯蔵所": ["屋外貯蔵所"],
    "販売取扱所": ["販売取扱所"],
}


@dataclass
class EquipmentHit:
    name: str
    confidence: float


def classify_equipment(text: str) -> list[EquipmentHit]:
    results: list[EquipmentHit] = []
    for eq, kws in RULES.items():
        score = 0.0
        for kw in kws:
            count = text.count(kw)
            if count > 0:
                score += min(0.6, 0.2 * count)
        if score > 0:
            results.append(EquipmentHit(name=eq, confidence=min(0.98, 0.4 + score)))
    if not results:
        return [EquipmentHit(name="共通法令", confidence=0.6)]
    return sorted(results, key=lambda r: r.confidence, reverse=True)
