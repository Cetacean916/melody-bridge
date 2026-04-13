"""Artist name mapping: Korean → English/romanized variants."""

# Maps primary Korean name to a list of search variants.
ARTIST_MAP: dict[str, list[str]] = {
    # Korean idols
    "프로미스나인": ["fromis_9", "fromis9"],
    "에픽하이": ["EPIK HIGH", "Epik High"],
    "세븐틴": ["SEVENTEEN"],
    "엑소": ["EXO"],
    "르세라핌": ["LE SSERAFIM", "LE SSERAFIM", "LESSERAFIM"],
    "뉴진스": ["NewJeans", "New Jeans"],
    "블랙핑크": ["BLACKPINK"],
    "에스파": ["aespa"],
    "아이브": ["IVE"],
    "트와이스": ["TWICE"],
    "레드벨벳": ["Red Velvet"],
    "있지": ["ITZY"],
    "스트레이키즈": ["Stray Kids"],
    "투바투": ["TOMORROW X TOGETHER", "TXT"],
    "엔시티": ["NCT", "NCT 127", "NCT DREAM", "NCT U"],
    "아이유": ["IU"],
    "볼빨간사춘기": ["Bolbbalgan4", "BOL4"],
    "마마무": ["MAMAMOO"],
    "여자친구": ["GFRIEND", "GFriend"],
    "오마이걸": ["OH MY GIRL"],
    "워너원": ["Wanna One", "WannaOne"],
    "데이식스": ["DAY6"],
    "더보이즈": ["THE BOYZ"],
    "스테이씨": ["STAYC"],
    "케플러": ["Kep1er"],
    "제로베이스원": ["ZEROBASEONE", "ZB1"],
    "라이즈": ["RIIZE"],
    "보이넥스트도어": ["BOYNEXTDOOR"],
    "아이들": ["(G)I-DLE", "G-I-DLE", "(G)I-DLE"],
    "핫이슈": ["HOT ISSUE"],
    "프로미스나인": ["fromis_9", "fromis9"],
    "NCT 127": ["NCT 127"],
    "NCT DREAM": ["NCT DREAM"],
    # J-Pop / Japanese artists
    "中島美嘉": ["Nakashima Mika", "Mika Nakashima"],
    "藤田恵美": ["Emi Fujita", "Fujita Emi"],
    "宇多田ヒカル": ["Hikaru Utada", "Utada Hikaru"],
    "YOASOBI": ["YOASOBI"],
    "米津玄師": ["Kenshi Yonezu", "Yonezu Kenshi"],
    "あいみょん": ["Aimyon"],
    "King Gnu": ["King Gnu"],
    "Official髭男dism": ["Official Hige Dandism", "Official HIGE DANdism"],
    "back number": ["back number"],
    "Spitz": ["Spitz", "スピッツ"],
    "中島みゆき": ["Miyuki Nakajima", "Nakajima Miyuki"],
    "Le Couple": ["Le Couple"],
    "松任谷由実": ["Yumi Matsutoya", "Matsutoya Yumi"],
    "竹内まりや": ["Mariya Takeuchi", "Takeuchi Mariya"],
    "サカナクション": ["Sakanaction"],
    "BUMP OF CHICKEN": ["BUMP OF CHICKEN"],
    "RADWIMPS": ["RADWIMPS"],
    "嵐": ["Arashi"],
    "CAPSULE": ["CAPSULE"],
    "Perfume": ["Perfume"],
}

# Reverse lookup: variant → canonical Korean name
_REVERSE_MAP: dict[str, str] = {}
for canonical, variants in ARTIST_MAP.items():
    _REVERSE_MAP[canonical.lower()] = canonical
    for v in variants:
        _REVERSE_MAP[v.lower()] = canonical


def get_search_variants(artist: str) -> list[str]:
    """Get all searchable variants for an artist name."""
    variants = [artist]
    if artist in ARTIST_MAP:
        variants.extend(ARTIST_MAP[artist])
    return variants


def canonical_name(artist: str) -> str | None:
    """Find canonical Korean name from any variant."""
    return _REVERSE_MAP.get(artist.lower())
