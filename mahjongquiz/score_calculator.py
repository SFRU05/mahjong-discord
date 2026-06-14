"""
점수 계산기

한수 × 부수 → 기본점수 → 실제 지불 점수
기본점수 = 부수 × 2^(한수+2)
론 점수 = 기본점수 × 4 (100단위 올림)
쯔모:
  친(동가): 기본점수 × 2 × 3명
  자(비친): 친 기본점수×2, 비친 기본점수×1

만관 이상:
  만관 = 8000
  하네만 = 12000
  배만 = 16000
  삼배만 = 24000
  역만 = 32000 (친 48000)

도라: 1장당 1한
"""

from math import ceil


def basic_points(fu: int, han: int) -> int:
    """기본점수 계산"""
    return fu * (2 ** (han + 2))


def mangan_check(fu: int, han: int) -> str | None:
    """만관 이상 여부 체크"""
    bp = basic_points(fu, han)
    if han >= 13:
        return 'yakuman'
    if han >= 11:
        return 'sanbaiman'
    if han >= 8:
        return 'baiman'
    if han >= 6:
        return 'haneman'
    if han >= 5 or bp >= 2000:
        return 'mangan'
    return None


def calculate_score(
    fu: int,
    han: int,
    is_tsumo: bool,
    is_dealer: bool,  # 동가(친) 여부
    honba: int = 0,   # 본장
) -> dict:
    """
    점수 계산.
    Returns: {
        'total': 총 획득 점수,
        'payment': 지불 구조 설명,
        'ron_payment': 론일 때 지불 점수 (1명),
        'tsumo_dealer': 쯔모 시 친이 받는 점수/인,
        'tsumo_ko': 쯔모 시 비친이 받는 점수/인,
    }
    """
    level = mangan_check(fu, han)
    honba_bonus = honba * 300  # 론은 +300/본장, 쯔모는 각 +100

    if level == 'yakuman':
        if is_dealer:
            ron = 48000
            tsumo_each = 16000
        else:
            ron = 32000
            tsumo_dealer = 16000
            tsumo_ko = 8000
    elif level == 'sanbaiman':
        if is_dealer:
            ron = 36000
            tsumo_each = 12000
        else:
            ron = 24000
            tsumo_dealer = 12000
            tsumo_ko = 6000
    elif level == 'baiman':
        if is_dealer:
            ron = 24000
            tsumo_each = 8000
        else:
            ron = 16000
            tsumo_dealer = 8000
            tsumo_ko = 4000
    elif level == 'haneman':
        if is_dealer:
            ron = 18000
            tsumo_each = 6000
        else:
            ron = 12000
            tsumo_dealer = 6000
            tsumo_ko = 3000
    elif level == 'mangan':
        if is_dealer:
            ron = 12000
            tsumo_each = 4000
        else:
            ron = 8000
            tsumo_dealer = 4000
            tsumo_ko = 2000
    else:
        bp = basic_points(fu, han)
        if is_dealer:
            ron = _round100(bp * 6)
            tsumo_each = _round100(bp * 2)
        else:
            ron = _round100(bp * 4)
            tsumo_dealer = _round100(bp * 2)
            tsumo_ko = _round100(bp * 1)

    if is_tsumo:
        if is_dealer:
            total = tsumo_each * 3 + honba * 100 * 3
            payment_str = f'각 {tsumo_each + honba*100}점 × 3명'
            return {
                'total': total,
                'payment': payment_str,
                'level': level,
                'tsumo_each': tsumo_each,
                'honba_bonus': honba * 100,
            }
        else:
            total = tsumo_dealer + tsumo_ko * 2 + honba * 100 * 3
            payment_str = f'친 {tsumo_dealer + honba*100}점 / 비친 {tsumo_ko + honba*100}점'
            return {
                'total': total,
                'payment': payment_str,
                'level': level,
                'tsumo_dealer': tsumo_dealer,
                'tsumo_ko': tsumo_ko,
                'honba_bonus': honba * 100,
            }
    else:
        total = ron + honba_bonus
        return {
            'total': total,
            'payment': f'{total}점 (론)',
            'level': level,
            'ron': ron,
            'honba_bonus': honba_bonus,
        }


def _round100(x: int) -> int:
    """100 단위 올림"""
    return ceil(x / 100) * 100


def level_name(level: str | None) -> str:
    names = {
        'mangan': '만관',
        'haneman': '하네만',
        'baiman': '배만',
        'sanbaiman': '삼배만',
        'yakuman': '역만',
    }
    return names.get(level, '')