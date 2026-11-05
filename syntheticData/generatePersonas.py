"""Generate synthetic Tikit profiles without changing files, APIs, or the DB.

Run from the repository root:
    python syntheticData/generatePersonas.py
    python syntheticData/generatePersonas.py --count 100 --seed 42

Output: UTF-8 JSON on stdout; errors on stderr. Python standard library only.
Names may repeat and have no numeric suffix; IDs and emails identify users.
This supersedes the numbered-name proposal in personaDataDesign.md.
The proposed --output option is deferred; this script never saves data itself.
Profiles are analysis fixtures, not signup payloads (no passwords or consent).
"""

import argparse
from collections import Counter
import json
import random
import sys
import uuid


# Mirrored from backend/app/core/config.py to avoid importing backend services.
MBTI_TYPES = (
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
)
CATEGORIES = ("콘서트", "뮤지컬", "스포츠", "전시", "클래식", "연극")

# Category order follows CATEGORIES. These are fictional test assumptions,
# not measured preferences or claims about MBTI and personal tastes.
PERSONA_WEIGHTS = {
    "live_fan": (40, 20, 15, 10, 5, 10),
    "story_lover": (10, 35, 5, 10, 10, 30),
    "sports_fan": (15, 5, 55, 10, 5, 10),
    "art_explorer": (10, 10, 5, 45, 20, 10),
    "classic_lover": (10, 10, 5, 20, 45, 10),
}
FAMILY_NAMES = ("김", "이", "박", "최", "정", "강", "조", "윤", "장", "임")
GIVEN_NAMES = (
    "하늘", "서연", "지우", "도윤", "수빈", "민준", "예린", "시우",
    "지민", "서준", "유진", "다은", "현우", "지안", "은우", "소윤",
)
ID_NAMESPACE = uuid.UUID("59a91c68-f64a-5c25-9546-a35642644f90")


def balanced_assignments(values: tuple, count: int, rng: random.Random) -> list:
    """Allocate evenly, randomizing remainder recipients and final order."""
    order = list(values)
    rng.shuffle(order)
    repeats, remainder = divmod(count, len(order))
    assignments = order * repeats + order[:remainder]
    rng.shuffle(assignments)
    return assignments


def category_weights(persona: str, rng: random.Random) -> dict[str, int]:
    """Add small individual variations, then apportion exactly 100 points."""
    raw = [max(1, weight + rng.randint(-3, 3))
           for weight in PERSONA_WEIGHTS[persona]]
    total = sum(raw)
    # Integer remainders avoid floating-point tie ambiguity.
    quotients = [divmod(weight * 100, total) for weight in raw]
    points = [quotient for quotient, _ in quotients]
    remainder_order = sorted(range(len(raw)), key=lambda i: -quotients[i][1])
    for index in remainder_order[:100 - sum(points)]:
        points[index] += 1
    return dict(zip(CATEGORIES, points))


def validate_dataset(data: dict) -> None:
    """Reject malformed generated profiles before any JSON is emitted."""
    users = data["users"]
    count = data["metadata"]["count"]
    if len(users) != count:
        raise ValueError("Generated user count does not match metadata")
    for field in ("id", "email"):
        if len({user[field] for user in users}) != count:
            raise ValueError(f"Duplicate {field} in generated data")
    for user in users:
        if not 1 <= len(user["name"].strip()) <= 30:
            raise ValueError("Generated name must contain 1 to 30 characters")
        if user["mbti"] not in MBTI_TYPES or user["persona"] not in PERSONA_WEIGHTS:
            raise ValueError("Unknown MBTI or persona")
        weights = user["category_weights"]
        if (set(weights) != set(CATEGORIES)
                or any(type(weight) is not int or weight <= 0
                       for weight in weights.values())
                or sum(weights.values()) != 100):
            raise ValueError("Category weights must be positive integers totaling 100")
        preferred = sorted(CATEGORIES, key=lambda category: -weights[category])[:2]
        if user["preferred_categories"] != preferred:
            raise ValueError("Preferred categories must match the two highest weights")
    for field, choices in (("mbti", MBTI_TYPES), ("persona", PERSONA_WEIGHTS)):
        totals = Counter(user[field] for user in users)
        counts = [totals[choice] for choice in choices]
        if max(counts) - min(counts) > 1:
            raise ValueError(f"Unbalanced {field} distribution")


def generate_personas(count: int = 100, seed: int = 42) -> dict:
    """Return reproducible profiles; names can repeat, IDs/emails cannot.

    Reproducibility assumes the same Python and generator version. Emails
    repeat across runs; do not concatenate runs without handling duplicates.
    """
    if type(count) is not int or count <= 0:
        raise ValueError("count must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    personas = balanced_assignments(tuple(PERSONA_WEIGHTS), count, rng)
    mbtis = balanced_assignments(MBTI_TYPES, count, rng)
    users = []
    for number, (persona, mbti) in enumerate(zip(personas, mbtis), start=1):
        name = rng.choice(FAMILY_NAMES) + rng.choice(GIVEN_NAMES)
        weights = category_weights(persona, rng)
        users.append({
            "id": str(uuid.uuid5(ID_NAMESPACE, f"{seed}:{number}")),
            "name": name,
            "email": f"persona{number:04d}@example.com",
            "mbti": mbti,
            "persona": persona,
            "preferred_categories": sorted(
                CATEGORIES, key=lambda category: -weights[category]
            )[:2],
            "category_weights": weights,
        })
    data = {
        "metadata": {
            "schema_version": "1.0",
            "generator_version": "1.0",
            "count": count,
            "seed": seed,
            "synthetic": True,
        },
        "users": users,
    }
    validate_dataset(data)
    return data


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("count must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("count must be a positive integer")
    return number


def main() -> int:
    # Windows pipe encoding must also preserve Korean names and categories.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Generate synthetic Tikit user profiles as UTF-8 JSON on stdout.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--count", type=positive_integer, default=100,
                        help="number of synthetic users")
    parser.add_argument("--seed", type=int, default=42, help="reproducible random seed")
    args = parser.parse_args()
    try:
        data = generate_personas(args.count, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
