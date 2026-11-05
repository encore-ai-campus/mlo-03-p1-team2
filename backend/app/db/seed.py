"""Seed demo performances (기본 8건 + 추가 샘플). Run: python -m app.db.seed"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Performance

PERFORMANCES = [
    dict(id="city", category="콘서트", title="2026 시티 라이츠 페스티벌", english="CITY\nLIGHTS",
         sub="MUSIC FESTIVAL", image="photo-1470229722913-7c0e2dbbafd3", style="city",
         venue="올림픽공원 88잔디마당", date_label="2026.11.21 - 11.22", start_date=date(2026, 11, 21),
         price=99000, badge="단독 판매", tag="티킷 PICK", days=2, slots=["14:00", "18:00"]),
    dict(id="opera", category="뮤지컬", title="뮤지컬 〈오페라의 유령〉", english="The\nPhantom\nof the Opera",
         sub="THE MUSICAL", image="photo-1503095396549-807759245b35", style="opera",
         venue="샤롯데씨어터", date_label="2026.11.10 - 2027.01.31", start_date=date(2026, 11, 10),
         price=80000, badge="화제의 뮤지컬", tag="인기 급상승", days=7, slots=["14:00", "19:30"]),
    dict(id="color", category="전시", title="컬러 오브 모먼트 : 일상의 조각들", english="COLOR\nOF\nMOMENT",
         sub="COLLECT YOUR MOMENTS", image="photo-1579783902614-a3fb3927b6a5", style="art",
         venue="그라운드시소 성수", date_label="2026.11.05 - 2027.02.28", start_date=date(2026, 11, 5),
         price=18000, badge="새로운 시선", tag="추천 전시", days=7,
         slots=["10:00", "12:00", "14:00", "16:00"]),
    dict(id="jazz", category="콘서트", title="블루 아워 재즈 나이트", english="Blue Hour\nJazz Night",
         sub="A NIGHT TO REMEMBER", image="photo-1511192336575-5a79af67a629", style="jazz",
         venue="노들섬 라이브하우스", date_label="2026.11.14 - 11.15", start_date=date(2026, 11, 14),
         price=65000, badge="가을밤의 재즈", tag="매진 임박", days=2, slots=["18:00", "20:00"]),
    dict(id="baseball", category="스포츠", title="서울 베이스볼 올스타 매치", english="PLAY\nYOUR\nGAME.",
         sub="2026 BASEBALL ALL STARS", image="photo-1471295253337-3ceaaedca402", style="sport",
         venue="잠실야구장", date_label="2026.11.07 - 11.08", start_date=date(2026, 11, 7),
         price=25000, badge="스페셜 매치", tag="주말 추천", days=2, slots=["14:00", "18:00"]),
    dict(id="classic", category="클래식", title="가을을 닮은 선율 : 피아노 리사이틀", english="Autumn\nSonata",
         sub="PIANO RECITAL", image="photo-1520523839897-bd0b52f945a0", style="classic",
         venue="예술의전당 콘서트홀", date_label="2026.11.18 - 11.20", start_date=date(2026, 11, 18),
         price=50000, badge="깊어지는 선율", tag="티킷 PICK", days=3, slots=["19:30"]),
    dict(id="theater", category="연극", title="연극 〈우리가 빛나던 계절〉", english="우리가\n빛나던\n계절",
         sub="OUR SHINING DAYS", image="photo-1507676184212-d03ab07a01bf", style="theater",
         venue="대학로 아트원씨어터", date_label="2026.11.06 - 12.27", start_date=date(2026, 11, 6),
         price=35000, badge="마음을 잇는 이야기", tag="대학로 추천", days=7, slots=["15:00", "19:00"]),
    dict(id="dance", category="뮤지컬", title="뮤지컬 〈미드나잇 인 서울〉", english="MIDNIGHT\nIN SEOUL",
         sub="THE CITY IS YOUR STAGE", image="photo-1516280440614-37939bbacd81", style="dance",
         venue="블루스퀘어 신한카드홀", date_label="2026.11.13 - 12.20", start_date=date(2026, 11, 13),
         price=70000, badge="새로운 무대", tag="신규 오픈", days=7, slots=["14:30", "19:30"]),
]

# ── 추가 샘플 공연 ─────────────────────────────────────────────
# 공연마다 주제에 맞는 Unsplash 사진(images.unsplash.com 에서 열리는지 확인한 ID)을 씁니다.
SHOW_IMAGES = {
    "indie-forest": "photo-1441974231531-c6227db76b6e", "first-snow": "photo-1477601263568-180e2c6d046e",
    "rock-night": "photo-1498038432885-c6f3f1b912ee", "street-sound": "photo-1540039155733-5bb30b53aa14",
    "acoustic-lounge": "photo-1525201548942-d8732f6617a0", "countdown": "photo-1498931299472-f7a63a5a1cfa",
    "next-wave": "photo-1514525253161-7a46d19cd819", "lofi-sunset": "photo-1483412033650-1015ddeb83d1",
    "trot-gala": "photo-1511671782779-c97d3d27a1d4", "reunion": "photo-1514320291840-2e0a9bf2a9ae",
    "citypop-drive": "photo-1503899036084-c55cdd92da26", "electric-wave": "photo-1470225620780-dba8ba36b745",
    "folk-campfire": "photo-1475483768296-6163e08872a1", "starlight-hotel": "photo-1580809361436-42a7ec204889",
    "moon-letters": "photo-1532693322450-2cb5c511067d", "noir-detective": "photo-1440404653325-ab127d49abc1",
    "school-of-band": "photo-1508700115892-45ecd05ae2ad", "lost-kingdom": "photo-1518709268805-4e9042af9f23",
    "snow-village": "photo-1418985991508-e47386d96a71", "retro-radio": "photo-1468164016595-6108e4c60c8b",
    "blood-moon": "photo-1516339901601-2e1b62dc0c45", "two-of-us": "photo-1474552226712-ac0f0961a954",
    "circus-dream": "photo-1507608616759-54f48f0af0ee", "little-kitchen": "photo-1556910103-1c02745aae4d",
    "poets-garden": "photo-1466692476868-aef1dfb1e735", "table-talk": "photo-1497032628192-86f99bcd76bc",
    "last-train": "photo-1474487548417-781cb71495f3", "monday-9am": "photo-1497366216548-37526070297c",
    "locked-room": "photo-1489599849927-2ee91cede3ba", "hamlet-seoul": "photo-1507924538820-ede94a04019d",
    "grandma-garden": "photo-1416879595882-3373a0480b5b", "midnight-radio": "photo-1590602847861-f357a9332bbc",
    "off-to-work": "photo-1522881193457-37ae97c905bf", "sea-letters": "photo-1505142468610-359e7d316be0",
    "improv-night": "photo-1475721027785-f74eccf877e2", "winter-letters": "photo-1455390582262-044cdead277a",
    "little-cloud": "photo-1503454537195-1dcabb73ffb9", "ode-to-joy": "photo-1465847899084-d164df4dedc6",
    "string-dialogues": "photo-1612225330812-01a9c6b355ec", "new-year-waltz": "photo-1467810563316-b5476525c0f9",
    "cello-nocturne": "photo-1507838153414-b4b713384a76", "film-orchestra": "photo-1485846234645-a62644f84728",
    "baroque-time": "photo-1481627834876-b7833e8f5570", "rising-violin": "photo-1465821185615-20b3c2fbf41b",
    "nutcracker": "photo-1508807526345-15e9b5f4eaff", "aria-night": "photo-1514306191717-452ec28c7814",
    "piano-duo": "photo-1552422535-c45813c61732", "brunch-classic": "photo-1513883049090-d0b7439799bf",
    "winter-landscape": "photo-1491002052546-bf38f186af56", "light-garden": "photo-1563089145-599997674d42",
    "dino-world": "photo-1470071459604-3b5ec3a7fe05", "seoul-at-night": "photo-1546874177-9e664107314e",
    "little-forest": "photo-1418065460487-3e41a6c84dc5", "chair-time": "photo-1506439773649-6e0eb8cfb237",
    "impression": "photo-1545989253-02cc26577f88", "to-the-space": "photo-1446776811953-b23d57bd21aa",
    "hangul-design": "photo-1517154421773-0529f29ea451", "between-cuts": "photo-1513364776144-60967b0f800f",
    "clay-and-fire": "photo-1493106641515-6b5631de4bb9", "cat-museum": "photo-1495360010541-f48722b34f7d",
    "deep-blue": "photo-1544551763-46a013bb70d5", "seoul-derby": "photo-1546519638-68e109498ffc",
    "spike-it": "photo-1592656094267-764a45160876", "ice-classic": "photo-1580748141549-71748dbe0bdc",
    "final-round": "photo-1542751371-adc38448a05e", "on-ice": "photo-1515703407324-5f753afd8be8",
    "cup-final": "photo-1431324155629-1a6deb1dec8d", "title-fight": "photo-1549719386-74dfcbf7dbed",
    "wkbl-allstar": "photo-1519861531473-9200262188bf", "climb-up": "photo-1564769662533-4f00a87b4056",
    "ssireum": "photo-1517438322307-e67111335449", "ping-pong": "photo-1609710228159-0fa9bd7c0827",
}
# SHOW_IMAGES 에 없는 공연은 포스터 스타일별 기본 사진을 씁니다.
STYLE_IMAGES = {
    "city": "photo-1470229722913-7c0e2dbbafd3",
    "jazz": "photo-1511192336575-5a79af67a629",
    "opera": "photo-1503095396549-807759245b35",
    "dance": "photo-1516280440614-37939bbacd81",
    "art": "photo-1579783902614-a3fb3927b6a5",
    "sport": "photo-1471295253337-3ceaaedca402",
    "classic": "photo-1520523839897-bd0b52f945a0",
    "theater": "photo-1507676184212-d03ab07a01bf",
}
MAX_BOOKABLE_DAYS = 7  # 기존 데이터와 같이 예매 가능 날짜는 최대 7일


def _show(id, category, style, title, english, sub, venue, period, price, badge, tag, slots):
    """period: "2026.11.28" 또는 "2026.11.28~2027.01.10" 형식."""
    start_s, _, end_s = period.partition("~")
    start = datetime.strptime(start_s, "%Y.%m.%d").date()
    end = datetime.strptime(end_s or start_s, "%Y.%m.%d").date()
    if end == start:
        label = f"{start:%Y.%m.%d}"
    elif end.year == start.year:
        label = f"{start:%Y.%m.%d} - {end:%m.%d}"
    else:
        label = f"{start:%Y.%m.%d} - {end:%Y.%m.%d}"
    return dict(id=id, category=category, title=title, english=english, sub=sub, image=SHOW_IMAGES.get(id, STYLE_IMAGES[style]),
                style=style, venue=venue, date_label=label, start_date=start,
                days=min((end - start).days + 1, MAX_BOOKABLE_DAYS), price=price, badge=badge, tag=tag, slots=slots)


EXTRA_PERFORMANCES = [_show(*row) for row in [
    # 콘서트
    ("indie-forest", "콘서트", "city", "숲속의 인디 페스타 2026", "INDIE\nFOREST", "OUTDOOR INDIE FESTIVAL",
     "난지한강공원", "2026.11.28~2026.11.29", 88000, "야외 페스티벌", "티킷 PICK", ["13:00", "17:00"]),
    ("first-snow", "콘서트", "jazz", "겨울 발라드 콘서트 〈첫눈의 기억〉", "First\nSnow", "BALLAD CONCERT",
     "세종문화회관 대극장", "2026.12.12~2026.12.14", 110000, "연말 콘서트", "매진 임박", ["18:00"]),
    ("rock-night", "콘서트", "city", "라우더 앤 라우더 : 록 나이트", "LOUDER\n& LOUDER", "ROCK LIVE NIGHT",
     "KBS아레나", "2026.11.21", 77000, "스탠딩 공연", "신규 오픈", ["19:00"]),
    ("street-sound", "콘서트", "city", "스트리트 사운드 힙합 페스티벌", "STREET\nSOUND", "HIPHOP FESTIVAL",
     "고척스카이돔", "2026.12.05~2026.12.06", 132000, "올스타 라인업", "인기 급상승", ["15:00", "19:00"]),
    ("acoustic-lounge", "콘서트", "jazz", "어쿠스틱 라운지 : 기타와 목소리", "Acoustic\nLounge", "UNPLUGGED LIVE",
     "홍대 웨스트브릿지", "2026.11.13~2026.11.15", 44000, "소극장 라이브", "주말 추천", ["17:00", "20:00"]),
    ("countdown", "콘서트", "city", "2027 카운트다운 뮤직 파티", "COUNT\nDOWN\n2027", "NEW YEAR'S EVE PARTY",
     "킨텍스 제2전시장", "2026.12.31", 143000, "연말 단독", "티킷 PICK", ["21:00"]),
    ("next-wave", "콘서트", "city", "넥스트 웨이브 K-POP 쇼케이스", "NEXT\nWAVE", "K-POP SHOWCASE",
     "올림픽공원 KSPO DOME", "2027.01.09~2027.01.10", 121000, "단독 판매", "인기 급상승", ["17:00"]),
    ("lofi-sunset", "콘서트", "jazz", "로파이 선셋 : 루프탑 라이브", "Lo-fi\nSunset", "ROOFTOP SESSION",
     "성수 루프탑 스테이지", "2026.11.08~2026.11.09", 39000, "감성 라이브", "신규 오픈", ["16:30"]),
    ("trot-gala", "콘서트", "city", "트로트 스타 갈라쇼", "TROT\nGALA", "STAR GALA SHOW",
     "부산 벡스코 오디토리움", "2026.12.19~2026.12.20", 99000, "온 가족 추천", "주말 추천", ["14:00", "18:00"]),
    ("reunion", "콘서트", "city", "다시 만난 밴드 : 리유니언 투어", "RE:\nUNION", "BAND REUNION TOUR",
     "대구 엑스코 동관", "2027.01.23~2027.01.24", 88000, "전국 투어", "매진 임박", ["18:00"]),
    ("citypop-drive", "콘서트", "jazz", "시티팝 나이트 드라이브", "City Pop\nDrive", "RETRO NIGHT",
     "블루스퀘어 마스터카드홀", "2026.11.27~2026.11.28", 66000, "레트로 감성", "추천 공연", ["19:30"]),
    ("electric-wave", "콘서트", "city", "일렉트릭 웨이브 EDM 페스티벌", "ELECTRIC\nWAVE", "EDM FESTIVAL",
     "인천 파라다이스시티 플라자", "2027.02.13~2027.02.14", 135000, "야간 페스티벌", "티킷 PICK", ["20:00"]),
    ("folk-campfire", "콘서트", "jazz", "포크 송 캠프파이어", "Folk\nCampfire", "FOLK SONG NIGHT",
     "제주아트센터", "2026.12.26~2026.12.27", 55000, "제주 공연", "힐링 추천", ["17:00"]),
    # 뮤지컬
    ("starlight-hotel", "뮤지컬", "dance", "뮤지컬 〈스타라이트 호텔〉", "STARLIGHT\nHOTEL", "THE MUSICAL",
     "충무아트센터 대극장", "2026.11.20~2027.02.15", 90000, "창작 뮤지컬", "신규 오픈", ["14:00", "19:30"]),
    ("moon-letters", "뮤지컬", "opera", "뮤지컬 〈달에게 보내는 편지〉", "Letters\nto the\nMoon", "THE MUSICAL",
     "세종문화회관 M씨어터", "2026.12.01~2027.01.25", 75000, "감동 실화", "인기 급상승", ["15:00", "20:00"]),
    ("noir-detective", "뮤지컬", "opera", "뮤지컬 〈느와르 탐정 사무소〉", "NOIR\nDETECTIVE", "MYSTERY MUSICAL",
     "디큐브 링크아트센터", "2026.11.15~2027.01.10", 85000, "미스터리 뮤지컬", "추천 공연", ["14:00", "19:00"]),
    ("school-of-band", "뮤지컬", "dance", "뮤지컬 〈스쿨 오브 밴드〉", "SCHOOL\nOF BAND", "ROCK MUSICAL",
     "홍익대 대학로 아트센터 대극장", "2026.12.10~2027.02.28", 66000, "청춘 록 뮤지컬", "주말 추천", ["15:00", "19:30"]),
    ("lost-kingdom", "뮤지컬", "opera", "뮤지컬 〈잃어버린 왕국〉", "The\nLost\nKingdom", "EPIC MUSICAL",
     "LG아트센터 서울", "2027.01.15~2027.03.29", 120000, "대형 뮤지컬", "티킷 PICK", ["14:00", "19:30"]),
    ("snow-village", "뮤지컬", "dance", "가족 뮤지컬 〈눈꽃 마을의 비밀〉", "SNOW\nVILLAGE", "FAMILY MUSICAL",
     "예스24스테이지 1관", "2026.12.20~2027.01.31", 40000, "가족 뮤지컬", "방학 추천", ["11:00", "14:00"]),
    ("retro-radio", "뮤지컬", "dance", "주크박스 뮤지컬 〈레트로 라디오〉", "RETRO\nRADIO", "JUKEBOX MUSICAL",
     "드림아트센터 1관", "2026.11.18~2027.01.18", 60000, "추억의 명곡", "인기 급상승", ["15:00", "20:00"]),
    ("blood-moon", "뮤지컬", "opera", "뮤지컬 〈블러드 문〉", "Blood\nMoon", "GOTHIC MUSICAL",
     "부산 드림씨어터", "2027.02.05~2027.04.04", 110000, "부산 단독", "신규 오픈", ["14:00", "19:00"]),
    ("two-of-us", "뮤지컬", "dance", "2인극 뮤지컬 〈우리 둘만의 계절〉", "JUST\nTWO OF US", "SMALL MUSICAL",
     "대학로 TOM 1관", "2026.11.12~2027.01.04", 55000, "소극장 뮤지컬", "대학로 추천", ["16:00", "20:00"]),
    ("circus-dream", "뮤지컬", "dance", "뮤지컬 〈서커스 드림〉", "CIRCUS\nDREAM", "SPECTACLE MUSICAL",
     "고양아람누리 아람극장", "2026.12.18~2027.02.07", 88000, "스펙터클", "주말 추천", ["14:00", "18:00"]),
    ("little-kitchen", "뮤지컬", "dance", "뮤지컬 〈마이 리틀 키친〉", "MY LITTLE\nKITCHEN", "COMEDY MUSICAL",
     "광림아트센터 BBCH홀", "2026.11.25~2027.01.26", 65000, "코미디 뮤지컬", "추천 공연", ["15:00", "19:30"]),
    ("poets-garden", "뮤지컬", "opera", "뮤지컬 〈시인의 정원〉", "The Poet's\nGarden", "THE MUSICAL",
     "국립극장 해오름극장", "2027.01.08~2027.02.21", 80000, "서정 뮤지컬", "새로운 무대", ["14:00", "19:30"]),
    # 연극
    ("table-talk", "연극", "theater", "연극 〈부엌 식탁 위의 대화〉", "부엌\n식탁\n대화", "TABLE TALK",
     "대학로 자유극장", "2026.11.10~2027.01.10", 30000, "가족 드라마", "대학로 추천", ["15:00", "19:30"]),
    ("last-train", "연극", "theater", "연극 〈마지막 기차〉", "마지막\n기차", "THE LAST TRAIN",
     "예술의전당 자유소극장", "2026.12.03~2026.12.28", 45000, "화제의 연극", "매진 임박", ["19:30"]),
    ("monday-9am", "연극", "theater", "코미디 연극 〈월요일 아침 9시〉", "월요일\n9시", "OFFICE COMEDY",
     "대학로 피카소극장", "2026.11.07~2027.02.28", 25000, "오픈런", "주말 추천", ["14:00", "17:00", "20:00"]),
    ("locked-room", "연극", "theater", "추리극 〈밀실의 손님〉", "밀실의\n손님", "THE LOCKED ROOM",
     "대학로 서경대학교 공연예술센터", "2026.11.14~2027.01.31", 35000, "관객 참여형", "인기 급상승", ["16:00", "19:30"]),
    ("hamlet-seoul", "연극", "theater", "연극 〈햄릿, 서울〉", "HAMLET\nSEOUL", "MODERN SHAKESPEARE",
     "국립극장 달오름극장", "2026.11.20~2026.12.13", 50000, "고전 재해석", "티킷 PICK", ["19:30"]),
    ("grandma-garden", "연극", "theater", "연극 〈할머니의 텃밭〉", "할머니의\n텃밭", "GRANDMA'S GARDEN",
     "세종문화회관 S씨어터", "2026.12.05~2026.12.30", 33000, "따뜻한 이야기", "가족 추천", ["14:00", "17:00"]),
    ("midnight-radio", "연극", "theater", "연극 〈심야 라디오〉", "심야\n라디오", "MIDNIGHT RADIO",
     "대학로 TOM 2관", "2026.11.19~2027.01.17", 30000, "공감 연극", "신규 오픈", ["17:00", "20:00"]),
    ("off-to-work", "연극", "theater", "1인극 〈나는 오늘도 출근한다〉", "오늘도\n출근", "ONE PERSON SHOW",
     "대학로 연우소극장", "2026.11.06~2026.11.30", 28000, "1인극", "대학로 추천", ["20:00"]),
    ("sea-letters", "연극", "theater", "연극 〈바다로 간 편지〉", "바다로\n간 편지", "LETTERS TO THE SEA",
     "부산 소향씨어터", "2027.01.09~2027.02.07", 38000, "부산 공연", "새로운 시선", ["15:00", "19:00"]),
    ("improv-night", "연극", "theater", "즉흥극 〈오늘 처음 만난 이야기〉", "IMPROV\nNIGHT", "IMPROVISATION SHOW",
     "홍대 산울림소극장", "2026.11.21~2026.12.20", 22000, "매회 다른 이야기", "주말 추천", ["19:00"]),
    ("winter-letters", "연극", "theater", "연극 〈겨울 편지〉", "겨울\n편지", "WINTER LETTERS",
     "명동예술극장", "2026.12.11~2027.01.11", 40000, "시대극", "추천 연극", ["15:00", "19:30"]),
    ("little-cloud", "연극", "theater", "어린이 인형극 〈꼬마 구름의 여행〉", "꼬마\n구름", "PUPPET THEATER",
     "국립극장 하늘극장", "2026.12.22~2027.02.22", 20000, "어린이 공연", "방학 추천", ["11:00", "14:00"]),
    # 클래식
    ("ode-to-joy", "클래식", "classic", "송년 음악회 : 합창 교향곡", "Ode\nto Joy", "YEAR-END CONCERT",
     "예술의전당 콘서트홀", "2026.12.28~2026.12.30", 90000, "송년 음악회", "티킷 PICK", ["19:30"]),
    ("string-dialogues", "클래식", "classic", "현의 대화 : 스트링 콰르텟", "String\nDialogues", "STRING QUARTET",
     "금호아트홀 연세", "2026.11.12~2026.11.13", 40000, "실내악", "추천 공연", ["19:30"]),
    ("new-year-waltz", "클래식", "classic", "신년 왈츠 콘서트", "New Year\nWaltz", "NEW YEAR CONCERT",
     "롯데콘서트홀", "2027.01.02~2027.01.03", 80000, "신년 음악회", "인기 급상승", ["17:00"]),
    ("cello-nocturne", "클래식", "classic", "첼로의 밤 : 무반주 모음곡", "Cello\nNocturne", "CELLO RECITAL",
     "IBK챔버홀", "2026.11.26", 45000, "단 하루", "매진 임박", ["20:00"]),
    ("film-orchestra", "클래식", "classic", "필름 오케스트라 : 영화 음악 콘서트", "Film\nOrchestra", "CINEMA IN CONCERT",
     "세종문화회관 대극장", "2026.11.29~2026.11.30", 70000, "영화 음악", "주말 추천", ["15:00", "19:00"]),
    ("baroque-time", "클래식", "classic", "바로크 타임머신", "Baroque\nTime", "EARLY MUSIC ENSEMBLE",
     "통영국제음악당", "2026.12.06~2026.12.07", 50000, "고음악", "새로운 선율", ["17:00"]),
    ("rising-violin", "클래식", "classic", "라이징 스타 바이올린 리사이틀", "Rising\nViolin", "VIOLIN RECITAL",
     "예술의전당 리사이틀홀", "2026.12.15~2026.12.16", 35000, "차세대 연주자", "신규 오픈", ["19:30"]),
    ("nutcracker", "클래식", "classic", "발레 〈호두까기 인형〉", "Nut\ncracker", "CHRISTMAS BALLET",
     "유니버설아트센터", "2026.12.18~2026.12.31", 70000, "크리스마스 발레", "티킷 PICK", ["14:00", "19:00"]),
    ("aria-night", "클래식", "classic", "오페라 갈라 : 아리아의 밤", "Aria\nNight", "OPERA GALA",
     "국립극장 해오름극장", "2026.11.27~2026.11.28", 60000, "오페라 갈라", "추천 공연", ["19:30"]),
    ("piano-duo", "클래식", "classic", "두 대의 피아노 : 피아노 듀오", "Piano\nDuo", "TWO PIANOS",
     "부산문화회관 중극장", "2027.01.16~2027.01.17", 40000, "부산 공연", "깊어지는 선율", ["17:00"]),
    ("brunch-classic", "클래식", "classic", "브런치 클래식 : 11시의 음악회", "11 O'clock\nClassic", "BRUNCH CONCERT",
     "성남아트센터 콘서트홀", "2026.11.11~2027.02.24", 25000, "마티네 공연", "힐링 추천", ["11:00"]),
    ("winter-landscape", "클래식", "classic", "국악 관현악 〈겨울 산수화〉", "Winter\nLandscape", "KOREAN ORCHESTRA",
     "국립국악원 예악당", "2027.01.22~2027.01.23", 30000, "국악 관현악", "새로운 시선", ["19:30"]),
    # 전시
    ("light-garden", "전시", "art", "빛의 정원 : 미디어아트展", "LIGHT\nGARDEN", "IMMERSIVE MEDIA ART",
     "동대문디자인플라자 아트홀", "2026.11.15~2027.03.15", 22000, "몰입형 전시", "티킷 PICK",
     ["10:00", "13:00", "16:00", "19:00"]),
    ("dino-world", "전시", "art", "공룡 대탐험 특별전", "DINO\nWORLD", "FAMILY EXHIBITION",
     "킨텍스 제1전시장", "2026.12.19~2027.02.28", 19000, "가족 전시", "방학 추천", ["10:00", "13:00", "16:00"]),
    ("seoul-at-night", "전시", "art", "서울의 밤 사진전", "SEOUL\nAT\nNIGHT", "PHOTO EXHIBITION",
     "세종문화회관 미술관", "2026.11.07~2027.01.18", 15000, "사진전", "신규 오픈", ["10:00", "14:00", "18:00"]),
    ("little-forest", "전시", "art", "그림책 원화전 : 작은 숲의 친구들", "LITTLE\nFOREST", "PICTURE BOOK ART",
     "예술의전당 한가람디자인미술관", "2026.11.20~2027.02.15", 16000, "그림책 원화", "가족 추천",
     ["10:00", "13:00", "16:00"]),
    ("chair-time", "전시", "art", "의자의 시간 : 디자인 체어展", "CHAIR\nTIME", "DESIGN EXHIBITION",
     "성수 S팩토리", "2026.12.01~2027.01.31", 18000, "디자인 전시", "추천 전시", ["11:00", "14:00", "17:00"]),
    ("impression", "전시", "art", "빛을 그린 화가들 : 인상주의 판화전", "Impression\nof Light", "PRINTS EXHIBITION",
     "더현대 서울 ALT.1", "2026.11.28~2027.03.01", 20000, "명화 전시", "인기 급상승", ["10:30", "13:30", "16:30"]),
    ("to-the-space", "전시", "art", "우주로 가는 길 : 과학 체험전", "TO THE\nSPACE", "SCIENCE EXPERIENCE",
     "국립과천과학관 특별전시관", "2026.12.20~2027.02.22", 14000, "체험형 전시", "방학 추천",
     ["10:00", "13:00", "15:00"]),
    ("hangul-design", "전시", "art", "한글, 디자인이 되다", "한글\n디자인", "HANGUL TYPOGRAPHY",
     "국립한글박물관 기획전시실", "2026.11.09~2027.01.25", 10000, "타이포그래피", "새로운 시선", ["10:00", "14:00"]),
    ("between-cuts", "전시", "art", "웹툰 원화 특별전 : 컷과 컷 사이", "BETWEEN\nCUTS", "WEBTOON EXHIBITION",
     "그라운드시소 서촌", "2026.12.05~2027.03.07", 17000, "웹툰 전시", "인기 급상승",
     ["10:00", "13:00", "16:00", "19:00"]),
    ("clay-and-fire", "전시", "art", "흙과 불의 시간 : 현대 도예전", "Clay\n& Fire", "CONTEMPORARY CERAMICS",
     "국립현대미술관 서울", "2026.11.13~2027.02.08", 8000, "공예 전시", "추천 전시", ["10:00", "14:00"]),
    ("cat-museum", "전시", "art", "고양이 미술관", "CAT\nMUSEUM", "CATS IN ART",
     "부산 뮤지엄원", "2026.12.12~2027.03.28", 16000, "반려 감성", "주말 추천", ["10:00", "13:00", "16:00"]),
    ("deep-blue", "전시", "art", "딥 블루 : 디지털 오션展", "DEEP\nBLUE", "DIGITAL OCEAN",
     "제주 서귀포 미디어홀", "2026.11.21~2027.04.30", 21000, "제주 전시", "새로운 시선",
     ["10:00", "13:00", "16:00", "19:00"]),
    # 스포츠
    ("seoul-derby", "스포츠", "sport", "서울 더비 : 프로농구 라이벌전", "SEOUL\nDERBY", "BASKETBALL RIVALRY",
     "잠실실내체육관", "2026.11.22", 22000, "라이벌 매치", "주말 추천", ["14:00"]),
    ("spike-it", "스포츠", "sport", "겨울 배구 V-클래식 매치", "SPIKE\nIT!", "VOLLEYBALL CLASSIC",
     "장충체육관", "2026.12.06~2026.12.07", 18000, "V-클래식", "인기 급상승", ["14:00", "19:00"]),
    ("ice-classic", "스포츠", "sport", "아이스하키 윈터 클래식", "ICE\nCLASSIC", "ICE HOCKEY MATCH",
     "목동 아이스링크", "2027.01.16~2027.01.17", 20000, "겨울 스포츠", "신규 오픈", ["15:00"]),
    ("final-round", "스포츠", "sport", "e스포츠 윈터 챔피언십 결승", "FINAL\nROUND", "ESPORTS CHAMPIONSHIP",
     "인스파이어 아레나", "2026.12.13", 45000, "결승전", "매진 임박", ["16:00"]),
    ("on-ice", "스포츠", "sport", "피겨 스케이팅 갈라 〈온 아이스〉", "ON\nICE", "FIGURE SKATING GALA",
     "고양어울림누리 아이스링크", "2026.12.26~2026.12.27", 66000, "갈라 쇼", "티킷 PICK", ["14:00", "18:00"]),
    ("cup-final", "스포츠", "sport", "코리아 축구 컵 결승전", "CUP\nFINAL", "FOOTBALL CUP FINAL",
     "서울월드컵경기장", "2026.11.29", 30000, "결승전", "티킷 PICK", ["15:00"]),
    ("title-fight", "스포츠", "sport", "링 위의 밤 : 복싱 타이틀 매치", "TITLE\nFIGHT", "BOXING NIGHT",
     "올림픽공원 핸드볼경기장", "2026.12.20", 55000, "타이틀 매치", "신규 오픈", ["19:00"]),
    ("wkbl-allstar", "스포츠", "sport", "여자프로농구 올스타전", "ALL\nSTAR", "WOMEN'S BASKETBALL",
     "부천체육관", "2027.01.03", 15000, "올스타전", "주말 추천", ["14:00"]),
    ("climb-up", "스포츠", "sport", "클라이밍 월드 투어 서울", "CLIMB\nUP", "CLIMBING WORLD TOUR",
     "인천 남동체육관", "2027.02.20~2027.02.21", 25000, "월드 투어", "새로운 시선", ["13:00", "17:00"]),
    ("ssireum", "스포츠", "sport", "설날 장사 씨름대회", "SSIREUM", "TRADITIONAL WRESTLING",
     "안산 상록수체육관", "2027.02.06~2027.02.09", 10000, "명절 특집", "가족 추천", ["13:00"]),
    ("ping-pong", "스포츠", "sport", "탁구 슈퍼매치", "PING\nPONG", "TABLE TENNIS SUPER MATCH",
     "수원실내체육관", "2026.11.15~2026.11.16", 12000, "슈퍼매치", "주말 추천", ["14:00"]),
]]

PERFORMANCES += EXTRA_PERFORMANCES


def seed(db: Session) -> int:
    """Upsert demo performances. Returns the number of rows written."""
    for data in PERFORMANCES:
        db.merge(Performance(**data))
    db.commit()
    return len(PERFORMANCES)


if __name__ == "__main__":
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        print(f"Seeded {seed(session)} performances")
