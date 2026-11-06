"""Generate synthetic Tikit profiles without changing files, APIs, or the DB.

Run from the repository root:
    python syntheticData/generatePersonas.py
    python syntheticData/generatePersonas.py --count 100 --seed 42

Output: UTF-8 JSON on stdout; errors on stderr. Python standard library only.
Names are sampled without replacement and have no numeric suffix.
This supersedes the numbered-name proposal in personaDataDesign.md.
The proposed --output option is deferred; this script never saves data itself.
Profiles are analysis fixtures, not signup payloads (no passwords or consent).
"""

import argparse
from collections import Counter
import json
from itertools import product
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
FAMILY_NAMES = (
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
    "노", "하", "곽", "성", "차", "주", "우", "구", "민", "진",
)
GIVEN_NAMES = (
    "하늘", "서연", "지우", "도윤", "수빈", "민준", "예린", "시우",
    "지민", "서준", "유진", "다은", "현우", "지안", "은우", "소윤",
    "가은", "건우", "경민", "나래", "다온", "도겸", "라온", "민서",
    "보민", "서아", "수현", "승우", "아린", "예준", "우진", "채원",
    "태윤", "하린", "해솔", "연우", "정우", "준서", "지호", "시윤",
    "도현", "예원", "수아", "세아", "서현", "지원", "유나", "은서",
    "태민", "성현", "재윤", "현서", "주원", "규리", "소율", "다인",
    "혜원", "윤서", "재이", "연서", "진우", "준영", "승현", "지율",
    "민재", "은채", "예담", "유찬", "태오", "선우", "수연", "재하",
    "소희", "현진", "지수", "정민", "혜린", "동현", "승민", "채린",
    "기현", "나윤", "다희", "로운", "명진", "보라", "솔비", "영준",
    "유림", "재원", "종현", "찬희", "태린", "하람", "희수", "한결",
)
# Deduplicate complete names as well, so future candidate edits remain safe.
NAME_POOL = tuple(dict.fromkeys(
    family + given for family in FAMILY_NAMES for given in GIVEN_NAMES
))
ID_NAMESPACE = uuid.UUID("59a91c68-f64a-5c25-9546-a35642644f90")

# Fictional simulation traits, independent of MBTI and observed behavior.
COMPANIONS = {
    "solo": "혼자", "friends": "친구들과", "partner": "연인과", "family": "가족과",
}
ATTENDANCE_FREQUENCIES = {
    "occasional": "몇 달에 한 번", "monthly": "한 달에 한두 번", "frequent": "거의 매주",
}
DISCOVERY_STYLES = {
    "familiar": "익숙한 아티스트와 작품을 주로 찾아요",
    "mixed": "익숙한 작품과 새로운 작품을 번갈아 찾아요",
    "adventurous": "처음 접하는 아티스트와 작품도 적극적으로 찾아요",
}
STYLE_OPTIONS = tuple(product(COMPANIONS, ATTENDANCE_FREQUENCIES, DISCOVERY_STYLES))


def profile_bio(preferred: list[str], style: dict[str, str]) -> str:
    """Describe the stored preferences and traits without inventing extra facts."""
    return (
        f"{'·'.join(preferred)}에 관심이 많아요. "
        f"{ATTENDANCE_FREQUENCIES[style['attendance_frequency']]} "
        f"{COMPANIONS[style['companion']]} 관람하고, "
        f"{DISCOVERY_STYLES[style['discovery_style']]}."
    )


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
    for field in ("id", "email", "name"):
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
        style = user.get("viewing_style", {})
        for field, choices in (
            ("companion", COMPANIONS),
            ("attendance_frequency", ATTENDANCE_FREQUENCIES),
            ("discovery_style", DISCOVERY_STYLES),
        ):
            if style.get(field) not in choices:
                raise ValueError(f"Unknown viewing_style {field}")
        if user.get("bio") != profile_bio(preferred, style):
            raise ValueError("bio must match preferred categories and viewing_style")
    for field, choices in (("mbti", MBTI_TYPES), ("persona", PERSONA_WEIGHTS)):
        totals = Counter(user[field] for user in users)
        counts = [totals[choice] for choice in choices]
        if max(counts) - min(counts) > 1:
            raise ValueError(f"Unbalanced {field} distribution")


def generate_personas(count: int = 100, seed: int = 42) -> dict:
    """Return reproducible profiles with unique names, IDs, and emails.

    Reproducibility assumes the same Python and generator version. Emails
    repeat across runs; do not concatenate runs without handling duplicates.
    """
    if type(count) is not int or count <= 0:
        raise ValueError("count must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if count > len(NAME_POOL):
        raise ValueError(f"count cannot exceed {len(NAME_POOL)} unique names")
    rng = random.Random(seed)
    personas = balanced_assignments(tuple(PERSONA_WEIGHTS), count, rng)
    mbtis = balanced_assignments(MBTI_TYPES, count, rng)
    names = rng.sample(NAME_POOL, count)
    users = []
    for number, (persona, mbti) in enumerate(zip(personas, mbtis), start=1):
        name = names[number - 1]
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
    # A separate stream preserves existing names, category scores, and identities.
    style_rng = random.Random(f"{seed}:viewing-style")
    for persona in PERSONA_WEIGHTS:
        group = [user for user in users if user["persona"] == persona]
        assignments = balanced_assignments(STYLE_OPTIONS, len(group), style_rng)
        for user, (companion, frequency, discovery) in zip(group, assignments):
            user["viewing_style"] = {
                "companion": companion,
                "attendance_frequency": frequency,
                "discovery_style": discovery,
            }
            user["bio"] = profile_bio(user["preferred_categories"], user["viewing_style"])
    data = {
        "metadata": {
            "schema_version": "1.1",
            "generator_version": "1.2",
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
