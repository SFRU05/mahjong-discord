"""
역(役) 계산기
리치마작의 주요 역을 계산합니다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collections import Counter

from tiles import (
    is_terminal, is_honor, is_terminal_or_honor,
    SANGENPAI, KAZEPAI, is_green, ZI
)
from .hand_generator import is_chiitoitsu, is_kokushi, count_tiles


def calculate_yaku(hand_info: dict, extra_conditions: dict) -> dict:
    """
    역 계산 메인 함수.

    hand_info: generate_random_winning_hand() 반환값
    extra_conditions: {
        'riichi': bool,
        'double_riichi': bool,
        'ippatsu': bool,
        'rinshan': bool,   # 영상개화
        'chankan': bool,   # 창깡
        'haitei': bool,    # 해저로어(쯔모)
        'houtei': bool,    # 하저로월(론)
    }

    Returns: {
        'yaku': [(name, han)],
        'total_han': int,
        'is_yakuman': bool,
        'yakuman_list': [(name, multiplier)]
    }
    """
    tiles = hand_info['tiles']
    head = hand_info['head']
    melds = hand_info['melds']
    meld_types = hand_info['meld_types']
    win_tile = hand_info['win_tile']
    is_tsumo = hand_info['is_tsumo']
    decomp_type = hand_info['decomp_type']
    seat_wind = hand_info['seat_wind']
    round_wind = hand_info['round_wind']

    yaku_list = []
    yakuman_list = []

    triplets = [m for t, m in zip(meld_types, melds) if t == 'triplet']
    kans = [m for t, m in zip(meld_types, melds) if t == 'kan']
    sequences = [m for t, m in zip(meld_types, melds) if t == 'sequence']
    triplet_like_count = len(triplets) + len(kans)

    # ─── 역만 체크 ───────────────────────────────────────────
    # 국사무쌍 / 국사무쌍 13면대기
    if is_kokushi(tiles):
        if _is_kokushi_13_wait(hand_info):
            yakuman_list.append(('국사무쌍 13면대기', 2))
        else:
            yakuman_list.append(('국사무쌍', 1))

    # 천화 / 지화
    if extra_conditions.get('tenhou'):
        yakuman_list.append(('천화', 1))
    if extra_conditions.get('chiihou'):
        yakuman_list.append(('지화', 1))

    if decomp_type == 'standard':
        # 대삼원
        sangenpai_triplets = [m for m in triplets if m[0] in SANGENPAI]
        if len(sangenpai_triplets) == 3:
            yakuman_list.append(('대삼원', 1))

        # 소사희 / 대사희
        kaze_triplets = sum(1 for m in triplets if m[0] in KAZEPAI)
        kaze_head = head[0] in KAZEPAI if head else False
        if kaze_triplets == 4:
            yakuman_list.append(('대사희', 2))
        elif kaze_triplets == 3 and kaze_head:
            yakuman_list.append(('소사희', 1))

        # 자일색 / 녹일색 / 청노두
        if all(is_honor(t) for t in tiles):
            yakuman_list.append(('자일색', 1))
        if all(is_green(t) for t in tiles):
            yakuman_list.append(('녹일색', 1))
        if all(is_terminal(t) for t in tiles):
            yakuman_list.append(('청노두', 1))

        # 사암각 / 사암각 단기
        if triplet_like_count == 4 and len(kans) == 0:
            if head and win_tile in head:
                yakuman_list.append(('사암각 단기', 2))
            else:
                yakuman_list.append(('사암각', 1))

        # 사깡쯔
        if len(kans) == 4:
            yakuman_list.append(('사깡쯔', 1))

        # 구련보등 / 순정구련보등
        chuuren_info = _chuuren_info(tiles, hand_info)
        if chuuren_info is not None:
            yakuman_list.append((chuuren_info['name'], chuuren_info['multiplier']))

    if yakuman_list:
        return {
            'yaku': [],
            'total_han': sum(m for _, m in yakuman_list) * 13,
            'is_yakuman': True,
            'yakuman_list': yakuman_list,
        }

    # ─── 일반 역 체크 ─────────────────────────────────────────

    # 쯔모
    if is_tsumo and decomp_type != 'kokushi':
        yaku_list.append(('멘젠쯔모', 1))

    # 리치 / 더블리치
    if extra_conditions.get('double_riichi'):
        yaku_list.append(('더블리치', 2))
    elif extra_conditions.get('riichi'):
        yaku_list.append(('리치', 1))

    # 일발
    if extra_conditions.get('ippatsu') and (extra_conditions.get('riichi') or extra_conditions.get('double_riichi')):
        yaku_list.append(('일발', 1))

    # 해저로어 / 하저로월
    if extra_conditions.get('haitei') and is_tsumo:
        yaku_list.append(('해저로어', 1))
    elif extra_conditions.get('houtei') and not is_tsumo:
        yaku_list.append(('하저로월', 1))

    # 영상개화
    if extra_conditions.get('rinshan'):
        yaku_list.append(('영상개화', 1))

    # 창깡
    if extra_conditions.get('chankan'):
        yaku_list.append(('창깡', 1))

    if decomp_type == 'chiitoitsu':
        yaku_list.append(('치또이쯔', 2))
        if all(not is_terminal_or_honor(t) for t in tiles):
            yaku_list.append(('탕야오', 1))

    elif decomp_type == 'standard':
        # 탕야오
        if all(not is_terminal_or_honor(t) for t in tiles):
            yaku_list.append(('탕야오', 1))

        # 핀후: 4순자 + 쌍면대기 + 머리가 역패 아님
        head_tile = head[0] if head else None
        is_pinfu = (
            len(sequences) == 4 and
            head_tile not in SANGENPAI and
            head_tile != seat_wind and
            head_tile != round_wind and
            _is_ryanmen(win_tile, melds, meld_types)
        )
        if is_pinfu:
            yaku_list.append(('핀후', 1))

        # 이페코 / 량페코 (멘젠 한정)
        ipeiko_count = _count_ipeiko(sequences)
        if ipeiko_count >= 2:
            yaku_list.append(('량페코', 3))
        elif ipeiko_count == 1:
            yaku_list.append(('이페코', 1))

        # 역패 (삼원패)
        for t in SANGENPAI:
            if any(m[0] == t for m in triplets):
                yaku_list.append((f'역패({_zi_name(t)})', 1))

        # 역패 (자풍/장풍)
        if any(m[0] == seat_wind for m in triplets):
            yaku_list.append((f'자풍({_zi_name(seat_wind)})', 1))
        if any(m[0] == round_wind for m in triplets):
            yaku_list.append((f'장풍({_zi_name(round_wind)})', 1))

        # 삼색동순 / 삼색동각
        if _san_shoku_doujun(sequences):
            yaku_list.append(('삼색동순', 2))
        if _san_shoku_doukou(triplets):
            yaku_list.append(('삼색동각', 2))

        # 이기도 (1~9 순자)
        if _ikkitsuukan(sequences):
            yaku_list.append(('이기도', 2))

        # 혼전대요구 / 준전대요구
        if _honitsu_tanyao(tiles, melds, meld_types, head):
            yaku_list.append(('혼전대요구', 2))
        if _junchantaiyao(tiles, melds, meld_types, head):
            yaku_list.append(('준전대요구', 3))

        # 삼암각 / 토이토이 / 소삼원
        if triplet_like_count == 3:
            yaku_list.append(('삼암각', 2))
        if triplet_like_count == 4:
            yaku_list.append(('토이토이', 2))

        sangenpai_heads = head[0] in SANGENPAI if head else False
        sangenpai_trips = sum(1 for m in triplets if m[0] in SANGENPAI)
        if sangenpai_trips == 2 and sangenpai_heads:
            yaku_list.append(('소삼원', 2))

        # 혼일색 / 청일색
        suits_used = {t[1] for t in tiles if t[1] != 'z'}
        has_honor = any(t[1] == 'z' for t in tiles)
        if len(suits_used) == 1 and has_honor:
            yaku_list.append(('혼일색', 3))
        if len(suits_used) == 1 and not has_honor:
            yaku_list.append(('청일색', 6))

    total_han = sum(h for _, h in yaku_list)

    return {
        'yaku': yaku_list,
        'total_han': total_han,
        'is_yakuman': False,
        'yakuman_list': []
    }


# ─── 헬퍼 함수들 ──────────────────────────────────────────────

def _zi_name(tile: str) -> str:
    names = {'1z':'동','2z':'남','3z':'서','4z':'북','5z':'백','6z':'발','7z':'중'}
    return names.get(tile, tile)

def _is_ryanmen(win_tile: str, melds: list, meld_types: list) -> bool:
    """쌍면 대기 여부"""
    for mtype, meld in zip(meld_types, melds):
        if mtype == 'sequence':
            nums = sorted(int(m[0]) for m in meld)
            suit = meld[0][1]
            wnum = int(win_tile[0]) if win_tile[1] != 'z' else -1
            if win_tile[1] == suit:
                if wnum == nums[0] and nums[0] > 1:
                    return True
                if wnum == nums[2] and nums[2] < 9:
                    return True
    return False

def _count_ipeiko(sequences: list) -> int:
    """이페코 수 계산"""
    seq_strs = [tuple(s) for s in sequences]
    count = 0
    used = [False] * len(seq_strs)
    for i in range(len(seq_strs)):
        for j in range(i+1, len(seq_strs)):
            if not used[i] and not used[j] and seq_strs[i] == seq_strs[j]:
                count += 1
                used[i] = used[j] = True
    return count

def _san_shoku_doujun(sequences: list) -> bool:
    """삼색동순"""
    nums_by_suit = {}
    for seq in sequences:
        suit = seq[0][1]
        num = int(seq[0][0])
        nums_by_suit.setdefault(suit, set()).add(num)
    for num in range(1, 8):
        if all(num in nums_by_suit.get(s, set()) for s in ['m','p','s']):
            return True
    return False

def _san_shoku_doukou(triplets: list) -> bool:
    """삼색동각"""
    nums_by_suit = {}
    for trip in triplets:
        suit = trip[0][1]
        if suit == 'z':
            continue
        num = trip[0][0]
        nums_by_suit.setdefault(num, set()).add(suit)
    return any(len(v) == 3 for v in nums_by_suit.values())

def _ikkitsuukan(sequences: list) -> bool:
    """이기도 (123, 456, 789 같은 수패로)"""
    for suit in ['m','p','s']:
        needed = {1, 4, 7}
        found = set()
        for seq in sequences:
            if seq[0][1] == suit:
                found.add(int(seq[0][0]))
        if needed.issubset(found):
            return True
    return False

def _honitsu_tanyao(tiles, melds, meld_types, head) -> bool:
    """혼전대요구: 모든 면자와 머리에 노두/자패 포함"""
    # 모든 면자에 노두/자패 있어야 함
    for mtype, meld in zip(meld_types, melds):
        if not any(is_terminal_or_honor(t) for t in meld):
            return False
    if head and not is_terminal_or_honor(head[0]):
        return False
    # 자패가 있어야 혼전 (준전과 구분)
    has_honor = any(is_honor(t) for t in tiles)
    return has_honor

def _junchantaiyao(tiles, melds, meld_types, head) -> bool:
    """준전대요구: 모든 면자와 머리에 노두패 포함, 자패 없음"""
    for mtype, meld in zip(meld_types, melds):
        if not any(is_terminal(t) for t in meld):
            return False
    if head and not is_terminal(head[0]):
        return False
    has_honor = any(is_honor(t) for t in tiles)
    return not has_honor


def _is_kokushi_13_wait(hand_info: dict) -> bool:
    """국사무쌍 13면대기 판정(완성된 손패와 화료패를 기준으로 근사 판정)."""
    tiles = hand_info['tiles']
    win_tile = hand_info['win_tile']
    if not is_kokushi(tiles):
        return False

    counts = count_tiles(tiles)
    if win_tile not in _KOKUSHI_SET:
        return False

    pair_tile = None
    for t in _KOKUSHI_SET:
        if counts.get(t, 0) == 2:
            pair_tile = t
            break

    if pair_tile is None:
        return False

    # 화료패가 쌍을 만든 패이고, 나머지는 모두 1장씩이면 13면대기로 간주
    return pair_tile == win_tile and all(counts.get(t, 0) == (2 if t == pair_tile else 1) for t in _KOKUSHI_SET)


def _chuuren_info(tiles: list, hand_info: dict) -> dict | None:
    """구련보등 / 순정구련보등 판정."""
    suits = {t[1] for t in tiles}
    if len(suits) != 1 or 'z' in suits:
        return None

    suit = next(iter(suits))
    counts = count_tiles(tiles)
    required = {f'1{suit}': 3, f'9{suit}': 3}
    for n in range(2, 9):
        required[f'{n}{suit}'] = 1

    if not all(counts.get(tile, 0) >= need for tile, need in required.items()):
        return None

    variant = (hand_info.get('yakuman_variant') or '').lower()
    if variant in {'pure_chuuren', 'junsei_chuuren', 'chuuren_13wait', '13wait'}:
        return {'name': '순정구련보등', 'multiplier': 2}

    return {'name': '구련보등', 'multiplier': 1}


_KOKUSHI_SET = {'1m', '9m', '1p', '9p', '1s', '9s', '1z', '2z', '3z', '4z', '5z', '6z', '7z'}
