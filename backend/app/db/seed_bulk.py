"""대량 샘플 공연 생성기: 카테고리별로 정해진 단어 조합을 써서 공연 데이터를 만듭니다.

같은 시드값(random.Random)을 쓰므로 실행할 때마다 똑같은 데이터가 나와서
`python -m app.db.seed` 를 여러 번 실행해도 같은 id 의 공연을 덮어쓰기만 합니다.
사진은 images.unsplash.com 에서 열리는지 확인한 ID 만 씁니다.
"""
import random
from datetime import date, timedelta
from itertools import product

MAX_BOOKABLE_DAYS = 7  # 기존 데이터와 같이 예매 가능 날짜는 최대 7일
FIRST_DAY = date(2026, 11, 6)
LAST_START_OFFSET = 150  # 첫 공연일부터 약 5개월 안에서 시작


def period_fields(start: date, end: date) -> dict:
    """시작·종료일로 date_label, start_date, days 를 만듭니다."""
    if end == start:
        label = f"{start:%Y.%m.%d}"
    elif end.year == start.year:
        label = f"{start:%Y.%m.%d} - {end:%m.%d}"
    else:
        label = f"{start:%Y.%m.%d} - {end:%Y.%m.%d}"
    return dict(date_label=label, start_date=start, days=min((end - start).days + 1, MAX_BOOKABLE_DAYS))


def _photos(*ids: str) -> list[str]:
    return [f"photo-{i}" for i in ids]


# ── 카테고리별 사진 묶음 ──────────────────────────────────────
CONCERT_PHOTOS = _photos(
    "1501386761578-eac5c94b800a", "1459749411175-04bf5292ceea", "1493225457124-a3eb161ffa5f",
    "1514525253161-7a46d19cd819", "1540039155733-5bb30b53aa14", "1492684223066-81342ee5ff30",
    "1506157786151-b8491531f063", "1429962714451-bb934ecdc4ec", "1470225620780-dba8ba36b745",
    "1516450360452-9312f5e86fc7", "1524368535928-5b5e00ddc76b", "1533174072545-7a4b6ad7a6c3",
    "1498038432885-c6f3f1b912ee", "1510915361894-db8b60106cb1", "1415201364774-f6f0bb35f28f",
    "1511671782779-c97d3d27a1d4", "1508700115892-45ecd05ae2ad", "1501612780327-45045538702b",
    "1478147427282-58a87a120781", "1468164016595-6108e4c60c8b", "1460723237483-7a6dc9d0b212",
    "1475721027785-f74eccf877e2", "1563841930606-67e2bce48b78", "1524650359799-842906ca1c06",
    "1496337589254-7e19d01cec44", "1504609813442-a8924e83f76e", "1499364615650-ec38552f4f34",
    "1483412033650-1015ddeb83d1", "1525201548942-d8732f6617a0", "1514320291840-2e0a9bf2a9ae",
    "1566737236500-c8ac43014a67", "1470229722913-7c0e2dbbafd3", "1511192336575-5a79af67a629",
)
MUSICAL_PHOTOS = _photos(
    "1514306191717-452ec28c7814", "1507924538820-ede94a04019d", "1580809361436-42a7ec204889",
    "1518834107812-67b0b7c58434", "1508807526345-15e9b5f4eaff", "1507608616759-54f48f0af0ee",
    "1467810563316-b5476525c0f9", "1498931299472-f7a63a5a1cfa", "1534447677768-be436bb09401",
    "1474552226712-ac0f0961a954", "1549490349-8643362247b5", "1557672172-298e090bd0f1",
    "1550859492-d5da9d8e45f3", "1518709268805-4e9042af9f23", "1516339901601-2e1b62dc0c45",
    "1532693322450-2cb5c511067d", "1462331940025-496dfbfc7564", "1519681393784-d120267933ba",
    "1503095396549-807759245b35", "1516280440614-37939bbacd81",
)
THEATER_PHOTOS = _photos(
    "1489599849927-2ee91cede3ba", "1478720568477-152d9b164e26", "1478737270239-2f02b77fc618",
    "1590602847861-f357a9332bbc", "1474487548417-781cb71495f3", "1497032628192-86f99bcd76bc",
    "1497366216548-37526070297c", "1455390582262-044cdead277a", "1516414447565-b14be0adf13e",
    "1416879595882-3373a0480b5b", "1466692476868-aef1dfb1e735", "1481627834876-b7833e8f5570",
    "1493106819501-66d381c466f1", "1522881193457-37ae97c905bf", "1485846234645-a62644f84728",
    "1440404653325-ab127d49abc1", "1470071459604-3b5ec3a7fe05", "1475483768296-6163e08872a1",
    "1441974231531-c6227db76b6e", "1503454537195-1dcabb73ffb9", "1503602642458-232111445657",
    "1569017388730-020b5f80a004", "1507676184212-d03ab07a01bf",
)
CLASSIC_PHOTOS = _photos(
    "1465847899084-d164df4dedc6", "1507838153414-b4b713384a76", "1552422535-c45813c61732",
    "1465821185615-20b3c2fbf41b", "1612225330812-01a9c6b355ec", "1513883049090-d0b7439799bf",
    "1518834107812-67b0b7c58434", "1508807526345-15e9b5f4eaff", "1580809361436-42a7ec204889",
    "1514306191717-452ec28c7814", "1467810563316-b5476525c0f9", "1481627834876-b7833e8f5570",
    "1491002052546-bf38f186af56", "1477601263568-180e2c6d046e", "1512389142860-9c449e58a543",
    "1543589077-47d81606c1bf", "1506318137071-a8e063b4bec0", "1519681393784-d120267933ba",
    "1520523839897-bd0b52f945a0",
)
EXHIBITION_PHOTOS = _photos(
    "1518998053901-5348d3961a04", "1531058020387-3be344556be6", "1536924940846-227afb31e2a5",
    "1545989253-02cc26577f88", "1541961017774-22349e4a1262", "1547891654-e66ed7ebb968",
    "1563089145-599997674d42", "1518791841217-8f162f1e1131", "1514888286974-6c03e2ca1dba",
    "1446776811953-b23d57bd21aa", "1451187580459-43490279c0fa", "1505142468610-359e7d316be0",
    "1544551763-46a013bb70d5", "1565193566173-7a0ee3dbe261", "1517154421773-0529f29ea451",
    "1538485399081-7191377e8241", "1546874177-9e664107314e", "1506439773649-6e0eb8cfb237",
    "1513364776144-60967b0f800f", "1460661419201-fd4cecdf8a8b", "1534796636912-3b95b3ab5986",
    "1495360010541-f48722b34f7d", "1573865526739-10659fec78a5", "1513360371669-4adf3dd7dff8",
    "1493106641515-6b5631de4bb9", "1503899036084-c55cdd92da26", "1452860606245-08befc0ff44b",
    "1561214115-f2f134cc4912", "1558591710-4b4a1ae0f04d", "1513475382585-d06e58bcb0e0",
    "1549490349-8643362247b5", "1557672172-298e090bd0f1", "1550859492-d5da9d8e45f3",
    "1462331940025-496dfbfc7564", "1579783902614-a3fb3927b6a5",
)

# ── 카테고리별 단어 · 장소 · 가격 ──────────────────────────────
TAGS = ["티킷 PICK", "인기 급상승", "신규 오픈", "매진 임박", "주말 추천", "추천 공연"]

CONCERT = dict(
    slug="concert", category="콘서트",
    adjs=[("블루", "BLUE"), ("미드나잇", "MIDNIGHT"), ("실버", "SILVER"), ("네온", "NEON"), ("썸머", "SUMMER"),
          ("문라이트", "MOONLIGHT"), ("골든", "GOLDEN"), ("와일드", "WILD"), ("레드", "RED"), ("오로라", "AURORA"),
          ("선셋", "SUNSET"), ("코스믹", "COSMIC")],
    nouns=[("하이웨이", "HIGHWAY"), ("클럽", "CLUB"), ("웨이브", "WAVE"), ("로드", "ROAD"), ("시티", "CITY"),
           ("가든", "GARDEN"), ("라디오", "RADIO"), ("트레인", "TRAIN"), ("하츠", "HEARTS"), ("플라워즈", "FLOWERS")],
    formats=[("단독 콘서트", "LIVE CONCERT"), ("전국 투어", "NATIONAL TOUR"), ("라이브 투어", "LIVE TOUR"),
             ("앙코르 콘서트", "ENCORE CONCERT"), ("쇼케이스", "SHOWCASE"), ("팬 콘서트", "FAN CONCERT")],
    venues=["올림픽공원 올림픽홀", "올림픽공원 핸드볼경기장", "블루스퀘어 마스터카드홀", "예스24라이브홀", "무신사 개러지",
            "홍대 롤링홀", "KBS아레나", "부산 벡스코 오디토리움", "대구 엑스코 동관", "광주 김대중컨벤션센터",
            "대전컨벤션센터", "인스파이어 아레나", "수원컨벤션센터", "제주아트센터"],
    prices=[55000, 66000, 77000, 88000, 99000, 110000, 121000, 132000, 143000],
    badges=["단독 판매", "전국 투어", "스탠딩 공연", "연말 콘서트", "올스타 라인업", "감성 라이브"],
    slots=[["18:00"], ["19:00"], ["19:30"], ["17:00", "20:00"], ["14:00", "18:00"]],
    duration=(0, 2), styles=["city", "jazz"], photos=CONCERT_PHOTOS,
)
MUSICAL = dict(
    slug="musical", category="뮤지컬",
    adjs=[("달빛", "Moonlit"), ("겨울", "Winter"), ("푸른", "Blue"), ("마지막", "Last"), ("작은", "Little"),
          ("황금", "Golden"), ("비밀의", "Secret"), ("잃어버린", "Lost"), ("붉은", "Crimson"), ("별빛", "Starlit"),
          ("한여름", "Midsummer"), ("오래된", "Old")],
    nouns=[("정원", "Garden"), ("왕국", "Kingdom"), ("약속", "Promise"), ("극장", "Theater"), ("서커스", "Circus"),
           ("등대", "Lighthouse"), ("우체국", "Post Office"), ("도서관", "Library"), ("소년", "Boy"),
           ("여왕", "Queen"), ("무도회", "Ball"), ("기차역", "Station")],
    formats=[("뮤지컬", "THE MUSICAL"), ("창작 뮤지컬", "ORIGINAL MUSICAL"), ("가족 뮤지컬", "FAMILY MUSICAL"),
             ("소극장 뮤지컬", "SMALL MUSICAL"), ("록 뮤지컬", "ROCK MUSICAL")],
    venues=["샤롯데씨어터", "블루스퀘어 신한카드홀", "충무아트센터 대극장", "디큐브 링크아트센터", "세종문화회관 M씨어터",
            "LG아트센터 서울", "예스24스테이지 1관", "드림아트센터 1관", "홍익대 대학로 아트센터 대극장",
            "광림아트센터 BBCH홀", "부산 드림씨어터", "대구 계명아트센터", "고양아람누리 아람극장",
            "성남아트센터 오페라하우스"],
    prices=[50000, 60000, 70000, 80000, 90000, 110000, 130000, 150000],
    badges=["창작 뮤지컬", "화제의 뮤지컬", "대형 뮤지컬", "앙코르 공연", "새로운 무대", "가족 뮤지컬"],
    slots=[["14:00", "19:30"], ["15:00", "20:00"], ["14:00", "18:00"], ["19:30"], ["11:00", "14:00"]],
    duration=(30, 90), styles=["opera", "dance"], photos=MUSICAL_PHOTOS,
)
THEATER = dict(
    slug="theater", category="연극",
    adjs=[("오래된", "OLD"), ("낯선", "STRANGE"), ("따뜻한", "WARM"), ("조용한", "QUIET"), ("마지막", "LAST"),
          ("비 오는", "RAINY"), ("엄마의", "MOTHER'S"), ("우리들의", "OUR"), ("열두 시의", "MIDNIGHT"),
          ("그해 여름의", "THAT SUMMER'S"), ("첫 번째", "FIRST"), ("작은", "LITTLE")],
    nouns=[("식탁", "TABLE"), ("편지", "LETTER"), ("손님", "GUEST"), ("골목", "ALLEY"), ("옥상", "ROOFTOP"),
           ("약속", "PROMISE"), ("방", "ROOM"), ("정류장", "BUS STOP"), ("이웃", "NEIGHBOR"), ("일기", "DIARY"),
           ("고백", "CONFESSION"), ("사진관", "PHOTO STUDIO")],
    formats=[("연극", ""), ("코미디 연극", "COMEDY"), ("추리극", "MYSTERY"), ("2인극", "TWO-PERSON PLAY"),
             ("가족극", "FAMILY PLAY")],
    venues=["대학로 아트원씨어터", "대학로 자유극장", "대학로 TOM 1관", "대학로 TOM 2관", "대학로 연우소극장",
            "대학로 피카소극장", "예술의전당 자유소극장", "국립극장 달오름극장", "명동예술극장", "세종문화회관 S씨어터",
            "홍대 산울림소극장", "부산 소향씨어터", "대전예술의전당 앙상블홀", "광주 유스퀘어 문화관"],
    prices=[20000, 25000, 30000, 35000, 40000, 45000, 50000],
    badges=["마음을 잇는 이야기", "오픈런", "관객 참여형", "공감 연극", "화제의 연극", "고전 재해석"],
    slots=[["15:00", "19:30"], ["16:00", "20:00"], ["19:30"], ["14:00", "17:00", "20:00"], ["20:00"]],
    duration=(20, 80), styles=["theater"], photos=THEATER_PHOTOS,
)
CLASSIC = dict(
    slug="classic", category="클래식",
    adjs=[("겨울", "Winter"), ("봄의", "Spring"), ("달빛", "Moonlight"), ("고요한", "Serene"), ("푸른", "Blue"),
          ("황혼의", "Twilight"), ("새벽의", "Dawn"), ("별의", "Starry"), ("바다의", "Ocean"), ("숲의", "Forest")],
    nouns=[("소나타", "Sonata"), ("세레나데", "Serenade"), ("랩소디", "Rhapsody"), ("녹턴", "Nocturne"),
           ("판타지아", "Fantasia"), ("왈츠", "Waltz"), ("협주곡", "Concerto"), ("아리아", "Aria"),
           ("전주곡", "Prelude"), ("행진곡", "March")],
    formats=[("피아노 리사이틀", "PIANO RECITAL"), ("바이올린 리사이틀", "VIOLIN RECITAL"),
             ("첼로 리사이틀", "CELLO RECITAL"), ("실내악 콘서트", "CHAMBER MUSIC"), ("교향악 축제", "SYMPHONY"),
             ("오페라 갈라", "OPERA GALA"), ("발레 갈라", "BALLET GALA"), ("국악 관현악", "KOREAN ORCHESTRA")],
    venues=["예술의전당 콘서트홀", "예술의전당 IBK챔버홀", "롯데콘서트홀", "금호아트홀 연세", "세종문화회관 대극장",
            "국립극장 해오름극장", "통영국제음악당", "부산문화회관 대극장", "대구콘서트하우스", "성남아트센터 콘서트홀",
            "국립국악원 예악당", "아트센터 인천 콘서트홀", "고양아람누리 아람음악당"],
    prices=[20000, 30000, 40000, 50000, 60000, 80000, 100000],
    badges=["깊어지는 선율", "실내악", "차세대 연주자", "마티네 공연", "거장의 무대", "송년 음악회"],
    slots=[["19:30"], ["17:00"], ["20:00"], ["15:00", "19:30"], ["11:00"]],
    duration=(0, 2), styles=["classic"], photos=CLASSIC_PHOTOS,
)
EXHIBITION = dict(
    slug="exhibition", category="전시",
    adjs=[("빛의", "LIGHT"), ("색의", "COLOR"), ("시간의", "TIME"), ("바다의", "OCEAN"), ("도시의", "URBAN"),
          ("숲의", "FOREST"), ("꿈의", "DREAM"), ("기억의", "MEMORY"), ("우주의", "COSMIC"), ("고양이의", "CAT"),
          ("종이의", "PAPER"), ("유리의", "GLASS")],
    nouns=[("정원", "GARDEN"), ("방", "ROOM"), ("지도", "MAP"), ("산책", "WALK"), ("조각들", "FRAGMENTS"),
           ("풍경", "SCAPE"), ("기록", "ARCHIVE"), ("여행", "JOURNEY"), ("순간", "MOMENT"), ("미술관", "MUSEUM")],
    formats=[("특별전", "SPECIAL EXHIBITION"), ("사진전", "PHOTO EXHIBITION"), ("미디어아트展", "MEDIA ART"),
             ("체험전", "EXPERIENCE"), ("원화전", "ORIGINAL ARTWORKS"), ("기획전", "CURATED EXHIBITION")],
    venues=["그라운드시소 성수", "그라운드시소 서촌", "동대문디자인플라자 아트홀", "세종문화회관 미술관",
            "예술의전당 한가람미술관", "더현대 서울 ALT.1", "국립현대미술관 서울", "성수 S팩토리", "코엑스 아티움",
            "부산 뮤지엄원", "대구미술관", "국립아시아문화전당", "제주 서귀포 미디어홀", "롯데뮤지엄"],
    prices=[8000, 10000, 12000, 15000, 18000, 20000, 22000, 25000],
    badges=["몰입형 전시", "새로운 시선", "사진전", "체험형 전시", "가족 전시", "디자인 전시"],
    slots=[["10:00", "13:00", "16:00"], ["10:00", "14:00", "18:00"], ["11:00", "14:00", "17:00"],
           ["10:00", "13:00", "16:00", "19:00"]],
    duration=(40, 120), styles=["art"], photos=EXHIBITION_PHOTOS,
)
TEXT_CATEGORIES = [CONCERT, MUSICAL, THEATER, CLASSIC, EXHIBITION]

# 스포츠: 도시 대 도시 경기. 종목별로 경기장 이름과 사진을 따로 둡니다.
CITIES = [("서울", "SEOUL"), ("부산", "BUSAN"), ("인천", "INCHEON"), ("대구", "DAEGU"), ("광주", "GWANGJU"),
          ("대전", "DAEJEON"), ("울산", "ULSAN"), ("수원", "SUWON"), ("창원", "CHANGWON"), ("제주", "JEJU")]
SPORTS = [
    ("농구", "BASKETBALL", "실내체육관",
     _photos("1546519638-68e109498ffc", "1504450758481-7338eba7524a", "1519861531473-9200262188bf")),
    ("배구", "VOLLEYBALL", "실내체육관", _photos("1592656094267-764a45160876")),
    ("축구", "FOOTBALL", "월드컵경기장",
     _photos("1574629810360-7efbbe195018", "1579952363873-27f3bade9f55", "1431324155629-1a6deb1dec8d")),
    ("풋살", "FUTSAL", "풋살파크", _photos("1574629810360-7efbbe195018", "1579952363873-27f3bade9f55")),
    ("야구", "BASEBALL", "야구장", _photos("1471295253337-3ceaaedca402")),
    ("아이스하키", "ICE HOCKEY", "아이스링크", _photos("1515703407324-5f753afd8be8", "1580748141549-71748dbe0bdc")),
    ("탁구", "TABLE TENNIS", "실내체육관", _photos("1534158914592-062992fbe900", "1609710228159-0fa9bd7c0827")),
    ("e스포츠", "ESPORTS", "e스포츠 경기장",
     _photos("1542751371-adc38448a05e", "1511512578047-dfb367046420", "1538481199705-c710c4e965fc")),
]
MATCH_TYPES = ["정규리그", "라이벌전", "컵대회", "올스타 매치", "플레이오프", "개막전"]
SPORT_PRICES = [10000, 12000, 15000, 18000, 20000, 25000, 30000, 40000]
SPORT_BADGES = ["라이벌 매치", "스페셜 매치", "결승전", "겨울 스포츠", "홈 개막전", "올스타전"]
SPORT_SLOTS = [["14:00"], ["15:00"], ["19:00"], ["14:00", "19:00"], ["16:00"]]


def _dates(rng: random.Random, duration: tuple[int, int]) -> dict:
    start = FIRST_DAY + timedelta(days=rng.randint(0, LAST_START_OFFSET))
    return period_fields(start, start + timedelta(days=rng.randint(*duration)))


def _text_category(spec: dict, count: int) -> list[dict]:
    rng = random.Random(f"tikit-{spec['slug']}")
    names = rng.sample(list(product(spec["adjs"], spec["nouns"])), count)
    shows = []
    for n, ((adj_ko, adj_en), (noun_ko, noun_en)) in enumerate(names, 1):
        fmt_ko, fmt_en = rng.choice(spec["formats"])
        cat = spec["category"]
        if cat == "콘서트":
            title, english, sub = f"{adj_ko} {noun_ko} {fmt_ko}", f"{adj_en}\n{noun_en}", fmt_en
        elif cat == "뮤지컬":
            title, english, sub = f"{fmt_ko} 〈{adj_ko} {noun_ko}〉", f"The\n{adj_en}\n{noun_en}", fmt_en
        elif cat == "연극":
            title, english = f"{fmt_ko} 〈{adj_ko} {noun_ko}〉", f"{adj_ko}\n{noun_ko}"
            sub = f"{adj_en} {noun_en}" + (f" · {fmt_en}" if fmt_en else "")
        elif cat == "클래식":
            title, english, sub = f"{adj_ko} {noun_ko} : {fmt_ko}", f"{adj_en}\n{noun_en}", fmt_en
        else:  # 전시
            title, english, sub = f"{adj_ko} {noun_ko} {fmt_ko}", f"{adj_en}\n{noun_en}", fmt_en
        shows.append(dict(
            id=f"{spec['slug']}-{n:03d}", category=cat, title=title, english=english, sub=sub,
            image=rng.choice(spec["photos"]), style=rng.choice(spec["styles"]), venue=rng.choice(spec["venues"]),
            **_dates(rng, spec["duration"]), price=rng.choice(spec["prices"]), badge=rng.choice(spec["badges"]),
            tag=rng.choice(TAGS), slots=rng.choice(spec["slots"]),
        ))
    return shows


def _sports(count: int) -> list[dict]:
    rng = random.Random("tikit-sport")
    pairs = [(h, a, s) for h, a, s in product(CITIES, CITIES, SPORTS) if h != a]
    shows = []
    for n, ((home_ko, home_en), (away_ko, away_en), (sport_ko, sport_en, arena, photos)) in enumerate(
        rng.sample(pairs, count), 1
    ):
        shows.append(dict(
            id=f"sport-{n:03d}", category="스포츠", title=f"{home_ko} vs {away_ko} {sport_ko} {rng.choice(MATCH_TYPES)}",
            english=f"{home_en}\nvs {away_en}", sub=f"{sport_en} MATCH", image=rng.choice(photos), style="sport",
            venue=f"{home_ko} {arena}", **_dates(rng, (0, 1)), price=rng.choice(SPORT_PRICES),
            badge=rng.choice(SPORT_BADGES), tag=rng.choice(TAGS), slots=rng.choice(SPORT_SLOTS),
        ))
    return shows


def generate_performances(per_category: int = 100) -> list[dict]:
    """카테고리마다 per_category 건씩 샘플 공연을 만듭니다."""
    shows = [s for spec in TEXT_CATEGORIES for s in _text_category(spec, per_category)]
    return shows + _sports(per_category)
