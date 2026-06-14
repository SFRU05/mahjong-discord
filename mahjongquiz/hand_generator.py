"""
화료패 생성 및 분석 알고리즘
- 랜덤으로 유효한 화료 패를 생성
- 몸통(면자), 머리(작두)로 분해
- 화료 조건(론/쯔모) 결정
"""
import random
from typing import Optional
from tiles import (
    ALL_TILES, MAN, PIN, SOU, ZI,
    is_terminal, is_honor, is_terminal_or_honor,
    SANGENPAI, KAZEPAI
)


def count_tiles(tiles: list) -> dict:
    counts = {}
    for t in tiles:
        counts[t] = counts.get(t, 0) + 1
    return counts


def can_form_set(counts: dict, tile: str, is_triplet: bool) -> bool:
    if is_triplet:
        return counts.get(tile, 0) >= 3
    suit = tile[1]
    if suit == 'z':
        return False
    num = int(tile[0])
    if num > 7:
        return False
    t1 = tile
    t2 = f'{num+1}{suit}'
    t3 = f'{num+2}{suit}'
    return counts.get(t1, 0) >= 1 and counts.get(t2, 0) >= 1 and counts.get(t3, 0) >= 1


def decompose_hand(tiles: list) -> list:
    """
    14패 화료패를 (머리, [몸통...]) 형태로 분해.
    여러 분해 방법이 있을 수 있으므로 모두 반환.
    Returns: list of (head, melds) where
        head = (tile, tile)
        melds = list of (tile, tile, tile)  # 순자 or 각자
    """
    results = []
    counts = count_tiles(tiles)
    sorted_tiles = sorted(set(tiles))

    def try_decompose(cnts, remaining_melds, head_used):
        if all(v == 0 for v in cnts.values()):
            return [[]]

        # 첫 번째 남은 패 찾기
        tile = None
        for t in sorted(cnts.keys()):
            if cnts[t] > 0:
                tile = t
                break
        if tile is None:
            return []

        solutions = []

        # 머리로 사용
        if not head_used and cnts[tile] >= 2:
            cnts[tile] -= 2
            for rest in try_decompose(cnts, remaining_melds, True):
                solutions.append([('head', tile)] + rest)
            cnts[tile] += 2

        # 각자(triplet)로 사용
        if cnts[tile] >= 3:
            cnts[tile] -= 3
            for rest in try_decompose(cnts, remaining_melds - 1, head_used):
                solutions.append([('triplet', tile)] + rest)
            cnts[tile] += 3

        # 순자(sequence)로 사용
        suit = tile[1]
        if suit != 'z':
            num = int(tile[0])
            if num <= 7:
                t2 = f'{num+1}{suit}'
                t3 = f'{num+2}{suit}'
                if cnts.get(t2, 0) >= 1 and cnts.get(t3, 0) >= 1:
                    cnts[tile] -= 1
                    cnts[t2] -= 1
                    cnts[t3] -= 1
                    for rest in try_decompose(cnts, remaining_melds - 1, head_used):
                        solutions.append([('sequence', tile, t2, t3)] + rest)
                    cnts[tile] += 1
                    cnts[t2] += 1
                    cnts[t3] += 1

        return solutions

    cnts_copy = dict(counts)
    raw_solutions = try_decompose(cnts_copy, 4, False)

    for sol in raw_solutions:
        head = None
        melds = []
        for item in sol:
            if item[0] == 'head':
                head = (item[1], item[1])
            elif item[0] == 'triplet':
                melds.append((item[1], item[1], item[1]))
            elif item[0] == 'sequence':
                melds.append((item[1], item[2], item[3]))
        if head and len(melds) == 4:
            results.append((head, melds))

    return results


def is_chiitoitsu(tiles: list) -> bool:
    """치또이쯔(7쌍) 여부"""
    counts = count_tiles(tiles)
    pairs = sum(1 for v in counts.values() if v == 2)
    return pairs == 7 and len(counts) == 7


def is_kokushi(tiles: list) -> bool:
    """국사무쌍 여부"""
    kokushi_tiles = {'1m','9m','1p','9p','1s','9s','1z','2z','3z','4z','5z','6z','7z'}
    counts = count_tiles(tiles)
    present = set(t for t in kokushi_tiles if counts.get(t, 0) >= 1)
    has_pair = any(counts.get(t, 0) >= 2 for t in kokushi_tiles)
    return len(present) == 13 and has_pair


def generate_random_winning_hand(
    seat_wind: str = '1z',   # 자풍
    round_wind: str = '1z',  # 장풍
    tsumo: bool = True
) -> Optional[dict]:
    """
    유효한 화료패를 랜덤 생성.
    Returns dict with:
        tiles: 14패 전체
        head: 머리 (tuple)
        melds: 몸통 목록 (list of tuple)
        win_tile: 화료패
        is_tsumo: 쯔모 여부
        decomp_type: 'standard' | 'chiitoitsu' | 'kokushi'
    """
    max_attempts = 500
    for _ in range(max_attempts):
        hand_type = random.choices(
            ['standard', 'chiitoitsu'],
            weights=[85, 15]
        )[0]

        if hand_type == 'chiitoitsu':
            result = _generate_chiitoitsu(tsumo)
        else:
            result = _generate_standard(seat_wind, round_wind, tsumo)

        if result:
            return result

    return None


def _generate_standard(seat_wind, round_wind, tsumo) -> Optional[dict]:
    """일반 화료패 생성"""
    # 패 풀 (각 패 4장)
    pool = ALL_TILES * 4
    random.shuffle(pool)

    # 머리 선택
    head_tile = random.choice(ALL_TILES)
    hand = [head_tile, head_tile]
    pool_copy = list(pool)
    for t in hand:
        if t in pool_copy:
            pool_copy.remove(t)

    # 몸통 4개 생성
    melds = []
    attempts = 0
    while len(melds) < 4 and attempts < 200:
        attempts += 1
        meld_type = random.choice(['sequence', 'sequence', 'triplet'])
        if meld_type == 'triplet':
            tile = random.choice(ALL_TILES)
            needed = [tile, tile, tile]
        else:
            suit = random.choice([MAN, PIN, SOU])
            num = random.randint(1, 7)
            tile = f'{num}{suit}'
            needed = [f'{num}{suit}', f'{num+1}{suit}', f'{num+2}{suit}']

        available = True
        temp_pool = list(pool_copy)
        for t in needed:
            if t in temp_pool:
                temp_pool.remove(t)
            else:
                available = False
                break

        if available:
            pool_copy = temp_pool
            meld = tuple(sorted(needed) if meld_type == 'sequence' else needed)
            # sequence는 순서 정렬
            if meld_type == 'sequence':
                meld = (needed[0], needed[1], needed[2])
            melds.append((meld_type, meld))

    if len(melds) != 4:
        return None

    # 모든 패 합치기
    all_tiles = list(hand)
    for _, m in melds:
        all_tiles.extend(m)

    # 화료패 선택 (머리 또는 몸통의 마지막 패)
    win_tile = random.choice(all_tiles)

    return {
        'tiles': sorted(all_tiles),
        'head': (head_tile, head_tile),
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': seat_wind,
        'round_wind': round_wind,
    }


def _generate_chiitoitsu(tsumo) -> Optional[dict]:
    """치또이쯔 생성"""
    pool = ALL_TILES * 4
    random.shuffle(pool)

    chosen = []
    used = set()
    for tile in ALL_TILES:
        if tile not in used and pool.count(tile) >= 2:
            chosen.append(tile)
            used.add(tile)
        if len(chosen) == 7:
            break

    if len(chosen) != 7:
        return None

    tiles = []
    for t in chosen:
        tiles.extend([t, t])

    win_tile = random.choice(chosen)

    return {
        'tiles': sorted(tiles),
        'head': None,
        'melds': [],
        'meld_types': [],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'chiitoitsu',
        'seat_wind': '1z',
        'round_wind': '1z',
    }