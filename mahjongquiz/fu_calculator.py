"""
부수(符数) 계산기

부수 계산 규칙:
  기본부: 30부 (멘젠 론), 20부 (핀후 쯔모, 치또이쯔=25)
  머리: 역패 2부, 일반 0부
  몸통:
    순자: 0부
    각자(명각): 중장 2, 노두/자 4
    각자(암각): 중장 4, 노두/자 8
    깡(명깡): 중장 8, 노두/자 16
    깡(암깡): 중장 16, 노두/자 32
  대기:
    양면 0부, 간짱/변짱/단기 2부
  쯔모: +2부 (핀후 쯔모 제외)

  최종 부수는 10 단위로 올림 (절상)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tiles import is_terminal_or_honor, SANGENPAI, KAZEPAI, is_honor, tile_to_emoji


def calculate_fu(hand_info: dict, yaku_result: dict, extra_conditions: dict) -> int:
    """
    부수 계산.
    Returns: int (절상 후 부수)
    """
    decomp_type = hand_info['decomp_type']
    head = hand_info['head']
    melds = hand_info['melds']
    meld_types = hand_info['meld_types']
    win_tile = hand_info['win_tile']
    is_tsumo = hand_info['is_tsumo']
    seat_wind = hand_info['seat_wind']
    round_wind = hand_info['round_wind']
    yaku_names = [y[0] for y in yaku_result['yaku']]

    # 치또이쯔: 고정 25부
    if decomp_type == 'chiitoitsu':
        return 25

    # 핀후
    is_pinfu = '핀후' in yaku_names

    # 기본부
    if is_pinfu and is_tsumo:
        fu = 20
    elif is_tsumo:
        fu = 20
    else:
        fu = 30  # 멘젠 론

    # 머리 부수
    if head:
        head_tile = head[0]
        if head_tile in SANGENPAI:
            fu += 2
        elif head_tile == seat_wind:
            fu += 2
        elif head_tile == round_wind:
            fu += 2
        # 자풍=장풍이면 4부 (연풍패)
        if head_tile == seat_wind == round_wind:
            fu += 2  # 이미 2 더해짐, 총 4

    # 몸통 부수
    if not is_pinfu:
        for mtype, meld in zip(meld_types, melds):
            if mtype == 'sequence':
                continue
            # 각자
            tile = meld[0]
            is_honor_tile = is_terminal_or_honor(tile)
            # 암각 (모두 손패에서)
            base = (8 if is_honor_tile else 4)  # 암각 기준
            fu += base

    # 대기 부수 (핀후는 0)
    if not is_pinfu:
        wait_fu = _calc_wait_fu(win_tile, hand_info)
        fu += wait_fu

    # 쯔모 부수 (핀후 쯔모 제외)
    if is_tsumo and not is_pinfu:
        fu += 2

    # 10 단위 절상
    fu = _round_up_to_10(fu)
    return fu


def _calc_wait_fu(win_tile: str, hand_info: dict) -> int:
    """대기 부수 계산"""
    melds = hand_info['melds']
    meld_types = hand_info['meld_types']
    head = hand_info['head']

    # 단기대기 (머리로 화료)
    if head and win_tile in head:
        return 2

    for mtype, meld in zip(meld_types, melds):
        if win_tile not in meld:
            continue
        if mtype == 'triplet':
            continue  # 샨폰이면 나중에 처리

        # 순자
        nums = sorted(int(t[0]) for t in meld)
        suit = meld[0][1]
        wnum = int(win_tile[0])

        if wnum == nums[1]:
            return 2  # 간짱
        if wnum == nums[0] and nums[2] == 3:
            return 2  # 변짱 (123의 3)
        if wnum == nums[2] and nums[0] == 7:
            return 2  # 변짱 (789의 7)

    return 0  # 양면 or 샨폰


def _round_up_to_10(fu: int) -> int:
    """10 단위 절상"""
    return ((fu + 9) // 10) * 10


def calculate_fu_with_details(hand_info: dict, yaku_result: dict, extra_conditions: dict) -> dict:
    """
    부수 계산 (상세 내역 포함).
    Returns: {
        'fu': int (절상 후 부수),
        'details': [(설명, 부수), ...],
        'base_fu': int (절상 전 부수)
    }
    """
    decomp_type = hand_info['decomp_type']
    head = hand_info['head']
    melds = hand_info['melds']
    meld_types = hand_info['meld_types']
    win_tile = hand_info['win_tile']
    is_tsumo = hand_info['is_tsumo']
    seat_wind = hand_info['seat_wind']
    round_wind = hand_info['round_wind']
    yaku_names = [y[0] for y in yaku_result['yaku']]

    details = []

    # 치또이쯔: 고정 25부
    if decomp_type == 'chiitoitsu':
        details.append(('치또이쯔 (고정)', 25))
        return {
            'fu': 25,
            'details': details,
            'base_fu': 25
        }

    # 핀후
    is_pinfu = '핀후' in yaku_names

    # 기본부
    if is_pinfu and is_tsumo:
        details.append(('기본부 (핀후 쯔모)', 20))
        fu = 20
    elif is_tsumo:
        details.append(('기본부 (쯔모)', 20))
        fu = 20
    else:
        details.append(('기본부 (멘젠 론)', 30))
        fu = 30  # 멘젠 론

    # 머리 부수
    if head:
        head_tile = head[0]
        head_emoji = tile_to_emoji(head_tile)
        if head_tile in SANGENPAI:
            details.append((f'{head_emoji} 머리 (삼원패)', 2))
            fu += 2
        elif head_tile == seat_wind:
            details.append((f'{head_emoji} 머리 (자풍)', 2))
            fu += 2
        elif head_tile == round_wind:
            details.append((f'{head_emoji} 머리 (장풍)', 2))
            fu += 2
        # 자풍=장풍이면 4부 (연풍패)
        if head_tile == seat_wind == round_wind:
            details.append((f'{head_emoji} 머리 (연풍패 추가)', 2))
            fu += 2  # 이미 2 더해짐, 총 4

    # 몸통 부수
    if not is_pinfu:
        triplet_fu = 0
        for mtype, meld in zip(meld_types, melds):
            if mtype == 'sequence':
                continue
            # 각자
            tile = meld[0]
            tile_emoji = tile_to_emoji(tile)
            is_honor_tile = is_terminal_or_honor(tile)
            # 암각 (모두 손패에서)
            base = (8 if is_honor_tile else 4)  # 암각 기준
            triplet_fu += base
            if is_honor_tile:
                details.append((f"{tile_emoji} 암각 (자패/노두)", base))
            else:
                details.append((f"{tile_emoji} 암각 (중장)", base))
        fu += triplet_fu

    # 대기 부수 (핀후는 0)
    if not is_pinfu:
        wait_fu = _calc_wait_fu(win_tile, hand_info)
        wait_name = _get_wait_name(win_tile, hand_info)
        if wait_fu > 0:
            details.append((f"대기 ({wait_name})", wait_fu))
        else:
            details.append(('대기 (양면)', 0))
        fu += wait_fu

    # 쯔모 부수 (핀후 쯔모 제외)
    if is_tsumo and not is_pinfu:
        details.append(('쯔모', 2))
        fu += 2

    # 절상 전 부수
    base_fu = fu

    # 10 단위 절상
    fu = _round_up_to_10(fu)
    
    if fu != base_fu:
        details.append((f'절상 ({base_fu}부 → {fu}부)', fu - base_fu))

    return {
        'fu': fu,
        'details': details,
        'base_fu': base_fu
    }


def _get_wait_name(win_tile: str, hand_info: dict) -> str:
    """대기 종류 이름 반환"""
    melds = hand_info['melds']
    meld_types = hand_info['meld_types']
    head = hand_info['head']

    # 단기대기 (머리로 화료)
    if head and win_tile in head:
        return "단기 대기"

    for mtype, meld in zip(meld_types, melds):
        if win_tile not in meld:
            continue
        if mtype == 'triplet':
            continue  # 샨폰이면 나중에 처리

        # 순자
        nums = sorted(int(t[0]) for t in meld)
        suit = meld[0][1]
        wnum = int(win_tile[0])

        if wnum == nums[1]:
            return "간짱 대기"
        if wnum == nums[0] and nums[2] == 3:
            return "변짱 대기"
        if wnum == nums[2] and nums[0] == 7:
            return "변짱 대기"

    return "양면 대기"
