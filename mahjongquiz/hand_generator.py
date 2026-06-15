"""
화료패 생성 및 분석 알고리즘
- 랜덤으로 유효한 화료 패를 생성
- 몸통(면자), 머리(작두)로 분해
- 화료 조건(론/쯔모) 결정
"""
import random
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
        decomp_type: 'standard' | 'chiitoitsu' | 'yakuman'
    """
    max_attempts = 500
    for _ in range(max_attempts):
        # 역만 생성 확률 (10%)
        hand_type = random.choices(
            ['standard', 'chiitoitsu', 'yakuman'],
            weights=[75, 15, 10]
        )[0]

        if hand_type == 'yakuman':
            result = _generate_yakuman(tsumo)
        elif hand_type == 'chiitoitsu':
            result = _generate_chiitoitsu(tsumo)
        else:
            result = _generate_standard(seat_wind, round_wind, tsumo)

        if result:
            return result

    return None


def _generate_standard(seat_wind, round_wind, tsumo) -> Optional[dict]:
    """일반 화료패 생성 (완전 랜덤)"""
    # 패 풀 (각 패 4장)
    pool = ALL_TILES * 4
    random.shuffle(pool)

    # 머리 선택 (무작위)
    head_tile = random.choice(ALL_TILES)
    hand = [head_tile, head_tile]
    pool_copy = list(pool)
    for t in hand:
        if t in pool_copy:
            pool_copy.remove(t)

    # 몸통 4개 생성 (완전 랜덤)
    melds = []
    attempts = 0
    while len(melds) < 4 and attempts < 300:
        attempts += 1
        # 시퀀스 vs 트리플릿 확률 조정
        meld_type = random.choice(['sequence', 'sequence', 'sequence', 'triplet'])
        
        if meld_type == 'triplet':
            # 풀에서 무작위로 선택
            available_triplets = []
            for tile in ALL_TILES:
                temp_pool = list(pool_copy)
                needed = [tile, tile, tile]
                count = 0
                for t in needed:
                    if t in temp_pool:
                        temp_pool.remove(t)
                        count += 1
                if count == 3:
                    available_triplets.append(tile)
            
            if not available_triplets:
                continue
            
            tile = random.choice(available_triplets)
            needed = [tile, tile, tile]
        else:
            # 순자 생성 (무작위)
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
            if meld_type == 'sequence':
                meld = (needed[0], needed[1], needed[2])
            else:
                meld = tuple(needed)
            melds.append((meld_type, meld))

    if len(melds) != 4:
        return None

    # 모든 패 합치기
    all_tiles = list(hand)
    for _, m in melds:
        all_tiles.extend(m)

    # 화료패 선택 (무작위)
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
    """치또이쯔 생성 (완전 랜덤)"""
    # 패 풀 생성 및 섞기
    pool = list(ALL_TILES) * 4
    random.shuffle(pool)
    
    # 7쌍을 무작위로 선택
    # 패 풀에서 랜덤으로 선택된 패들 중에서 쌍을 만들기
    chosen = []
    tile_list = list(ALL_TILES)
    random.shuffle(tile_list)  # 패 종류를 무작위 순서로
    
    pool_pairs = {}
    for tile in pool:
        if tile not in pool_pairs:
            pool_pairs[tile] = 0
        pool_pairs[tile] += 1
    
    # 2개 이상 있는 패들 중에서 랜덤으로 7개 선택
    available_pairs = [tile for tile, count in pool_pairs.items() if count >= 2]
    if len(available_pairs) < 7:
        return None
    
    chosen = random.sample(available_pairs, 7)

    # 14패 생성 (7쌍)
    tiles = []
    for t in chosen:
        tiles.extend([t, t])

    # 화료패 선택 (무작위)
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


def _generate_yakuman(tsumo) -> Optional[dict]:
    """역만 생성 (대삼원, 소사희, 녹일색, 청노두 등)"""
    yakuman_types = ['daisangen', 'shousushi', 'ryokuitsu', 'honroutou']
    yakuman_type = random.choice(yakuman_types)
    
    if yakuman_type == 'daisangen':  # 대삼원
        return _generate_daisangen(tsumo)
    elif yakuman_type == 'shousushi':  # 소사희
        return _generate_shousushi(tsumo)
    elif yakuman_type == 'ryokuitsu':  # 녹일색
        return _generate_ryokuitsu(tsumo)
    else:  # 청노두
        return _generate_honroutou(tsumo)


def _generate_daisangen(tsumo) -> Optional[dict]:
    """대삼원 생성 (삼원패 3개 각자)"""
    # 삼원패: 5z(백), 6z(발), 7z(중)
    sangenpai = ['5z', '6z', '7z']
    
    # 각자 3개 (각각 3중)
    tiles = []
    melds = []
    for sp in sangenpai:
        tiles.extend([sp, sp, sp])
        melds.append(('triplet', (sp, sp, sp)))
    
    # 나머지 2개 순자/각자
    remaining_tiles = [t for t in ALL_TILES if t not in sangenpai]
    remaining_pool = remaining_tiles * 4
    random.shuffle(remaining_pool)
    pool_copy = list(remaining_pool)
    
    # 머리 선택
    head_tile = random.choice(remaining_tiles)
    head = (head_tile, head_tile)
    tiles.extend([head_tile, head_tile])
    for _ in range(2):
        if head_tile in pool_copy:
            pool_copy.remove(head_tile)
    
    # 몸통 1개 추가
    attempts = 0
    while len(melds) < 4 and attempts < 300:
        attempts += 1
        meld_type = random.choice(['sequence', 'triplet'])
        
        if meld_type == 'triplet':
            available_triplets = [t for t in remaining_tiles if pool_copy.count(t) >= 3]
            if available_triplets:
                tile = random.choice(available_triplets)
                melds.append(('triplet', (tile, tile, tile)))
                for _ in range(3):
                    pool_copy.remove(tile)
                tiles.extend([tile, tile, tile])
        else:
            # 순자 생성 (무작위)
            suit = random.choice([MAN, PIN, SOU])
            num = random.randint(1, 7)
            tile = f'{num}{suit}'
            needed = [f'{num}{suit}', f'{num+1}{suit}', f'{num+2}{suit}']
            if all(pool_copy.count(t) >= 1 for t in needed):
                melds.append(('sequence', tuple(needed)))
                for t in needed:
                    pool_copy.remove(t)
                    tiles.append(t)
    
    if len(melds) != 4:
        return None
    
    win_tile = random.choice(tiles)
    
    return {
        'tiles': sorted(tiles),
        'head': head,
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': '1z',
        'round_wind': '1z',
    }


def _generate_shousushi(tsumo) -> Optional[dict]:
    """소사희 생성 (3개 풍패 각자 + 1개 풍패 머리)"""
    kazepai = ['1z', '2z', '3z', '4z']  # 동남서북
    
    # 3개의 풍패를 각자로
    selected_kaze = random.sample(kazepai, 3)
    tiles = []
    melds = []
    for kaze in selected_kaze:
        tiles.extend([kaze, kaze, kaze])
        melds.append(('triplet', (kaze, kaze, kaze)))
    
    # 머리용 풍패 (남은 것 중 1개)
    head_kaze = [k for k in kazepai if k not in selected_kaze][0]
    tiles.extend([head_kaze, head_kaze])
    head = (head_kaze, head_kaze)
    
    # 나머지 1개 몸통
    remaining_tiles = [t for t in ALL_TILES if t[1] != 'z']
    remaining_pool = remaining_tiles * 4
    random.shuffle(remaining_pool)
    pool_copy = list(remaining_pool)
    
    attempts = 0
    while len(melds) < 4 and attempts < 200:
        attempts += 1
        meld_type = random.choice(['sequence', 'triplet'])
        
        if meld_type == 'triplet':
            available_triplets = [t for t in remaining_tiles if pool_copy.count(t) >= 3]
            if available_triplets:
                tile = random.choice(available_triplets)
                melds.append(('triplet', (tile, tile, tile)))
                for _ in range(3):
                    pool_copy.remove(tile)
                tiles.extend([tile, tile, tile])
        else:
            # 순자 생성
            suit = random.choice([MAN, PIN, SOU])
            num = random.randint(1, 7)
            tile = f'{num}{suit}'
            needed = [f'{num}{suit}', f'{num+1}{suit}', f'{num+2}{suit}']
            if all(pool_copy.count(t) >= 1 for t in needed):
                melds.append(('sequence', tuple(needed)))
                for t in needed:
                    pool_copy.remove(t)
                    tiles.append(t)
    
    if len(melds) != 4:
        return None
    
    win_tile = random.choice(tiles)
    
    return {
        'tiles': sorted(tiles),
        'head': head,
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': '1z',
        'round_wind': '1z',
    }


def _generate_jishantsu(tsumo) -> Optional[dict]:
    """자일색 생성 (모든 패가 자패)"""
    # 자패: 1z~7z (동남서북백발중)
    tiles = []
    pool = list(ZI) * 4
    random.shuffle(pool)
    
    # 머리 선택
    head_tile = random.choice(ZI)
    head = (head_tile, head_tile)
    tiles.extend([head_tile, head_tile])
    pool_copy = list(pool)
    for _ in range(2):
        if head_tile in pool_copy:
            pool_copy.remove(head_tile)
    
    # 몸통 4개 (모두 자패)
    melds = []
    attempts = 0
    while len(melds) < 4 and attempts < 200:
        attempts += 1
        
        # 사용 가능한 자패 찾기
        available_triplets = [t for t in ZI if pool_copy.count(t) >= 3]
        
        if not available_triplets:
            continue
        
        tile = random.choice(available_triplets)
        melds.append(('triplet', (tile, tile, tile)))
        for _ in range(3):
            pool_copy.remove(tile)
        tiles.extend([tile, tile, tile])
    
    if len(melds) != 4:
        return None
    
    win_tile = random.choice(tiles)
    
    return {
        'tiles': sorted(tiles),
        'head': head,
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': '1z',
        'round_wind': '1z',
    }


def _generate_honroutou(tsumo) -> Optional[dict]:
    """청노두 생성 (노두패와 자패만)"""
    # 노두패: 1m, 9m, 1p, 9p, 1s, 9s + 자패: 1z~7z
    terminal_honor_tiles = ['1m', '9m', '1p', '9p', '1s', '9s', '1z', '2z', '3z', '4z', '5z', '6z', '7z']
    
    tiles = []
    pool = terminal_honor_tiles * 4
    random.shuffle(pool)
    
    # 머리 선택
    head_tile = random.choice(terminal_honor_tiles)
    head = (head_tile, head_tile)
    tiles.extend([head_tile, head_tile])
    pool_copy = list(pool)
    for _ in range(2):
        if head_tile in pool_copy:
            pool_copy.remove(head_tile)
    
    # 몸통 4개
    melds = []
    attempts = 0
    while len(melds) < 4 and attempts < 300:
        attempts += 1
        available_triplets = [t for t in terminal_honor_tiles if pool_copy.count(t) >= 3]
        
        if not available_triplets:
            continue
        
        tile = random.choice(available_triplets)
        melds.append(('triplet', (tile, tile, tile)))
        for _ in range(3):
            pool_copy.remove(tile)
        tiles.extend([tile, tile, tile])
    
    if len(melds) != 4:
        return None
    
    win_tile = random.choice(tiles)
    
    return {
        'tiles': sorted(tiles),
        'head': head,
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': '1z',
        'round_wind': '1z',
    }


def _generate_ryokuitsu(tsumo) -> Optional[dict]:
    """녹일색 생성 (초록색 패만 사용)"""
    # 녹색 패: 2p, 3p, 4p, 6p, 8p, 2s, 3s, 4s, 6s, 8s, 5z(발)
    green_tiles = ['2p', '3p', '4p', '6p', '8p', '2s', '3s', '4s', '6s', '8s', '5z']
    
    tiles = []
    pool = green_tiles * 4
    random.shuffle(pool)
    
    # 머리 선택
    head_tile = random.choice(green_tiles)
    head = (head_tile, head_tile)
    tiles.extend([head_tile, head_tile])
    pool_copy = list(pool)
    for _ in range(2):
        if head_tile in pool_copy:
            pool_copy.remove(head_tile)
    
    # 몸통 4개 생성 - 시퀀스와 트리플렛
    melds = []
    attempts = 0
    while len(melds) < 4 and attempts < 300:
        attempts += 1
        meld_type = random.choice(['sequence', 'sequence', 'triplet'])
        
        if meld_type == 'triplet':
            available_triplets = [t for t in green_tiles if pool_copy.count(t) >= 3]
            if available_triplets:
                tile = random.choice(available_triplets)
                melds.append(('triplet', (tile, tile, tile)))
                for _ in range(3):
                    pool_copy.remove(tile)
                tiles.extend([tile, tile, tile])
        else:
            # 순자 (소련색이나 록색 내에서)
            suits = [t[1] for t in green_tiles if t[1] in ['p', 's']]
            suits = list(set(suits))
            
            if suits:
                suit = random.choice(suits)
                # 이 suit에서 가능한 sequence 찾기
                suited_tiles = [t for t in green_tiles if t[1] == suit]
                
                # 가능한 sequence 찾기
                possible_sequences = []
                for num in range(2, 7):  # 2p-4p, 3p-5p 등
                    tile = f'{num}{suit}'
                    if tile in green_tiles:
                        next1 = f'{num+1}{suit}'
                        next2 = f'{num+2}{suit}'
                        if next1 in green_tiles and next2 in green_tiles:
                            if pool_copy.count(tile) >= 1 and pool_copy.count(next1) >= 1 and pool_copy.count(next2) >= 1:
                                possible_sequences.append((tile, next1, next2))
                
                if possible_sequences:
                    seq = random.choice(possible_sequences)
                    melds.append(('sequence', seq))
                    for t in seq:
                        pool_copy.remove(t)
                        tiles.append(t)
    
    if len(melds) != 4:
        return None
    
    win_tile = random.choice(tiles)
    
    return {
        'tiles': sorted(tiles),
        'head': head,
        'melds': [m for _, m in melds],
        'meld_types': [t for t, _ in melds],
        'win_tile': win_tile,
        'is_tsumo': tsumo,
        'decomp_type': 'standard',
        'seat_wind': '1z',
        'round_wind': '1z',
    }

