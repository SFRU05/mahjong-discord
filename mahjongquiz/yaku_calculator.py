"""
역(役) 계산기
리치마작의 주요 역을 계산합니다.
"""

from tiles import (
    is_terminal, is_honor, is_terminal_or_honor,
    SANGENPAI, KAZEPAI, is_green, ZI
)
from hand_generator import is_chiitoitsu, is_kokushi, count_tiles


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

    # ─── 역만 체크 ───────────────────────────────────────────
    # 국사무쌍
    if decomp_type == 'standard' and is_kokushi(tiles):
        yakuman_list.append(('국사무쌍', 1))

    # 천화 / 지화
    if extra_conditions.get('tenhou'):
        yakuman_list.append(('천화', 1))
    elif extra_conditions.get('chiihou'):
        yakuman_list.append(('지화', 1))

    # 치또이쯔 관련 역만 없음 (그냥 2판)
    if decomp_type == 'chiitoitsu':
        pass  # 역만 없음

    if decomp_type == 'standard':
        triplets = [m for t, m in zip(meld_types, melds) if t == 'triplet']
        sequences = [m for t, m in zip(meld_types, melds) if t == 'sequence']

        # 대삼원
        sangenpai_triplets = [m for m in triplets if m[0] in SANGENPAI]
        if len(sangenpai_triplets) == 3:
            yakuman_list.append(('대삼원', 1))

        # 소사희 / 대사희
        kaze_triplets = sum(1 for m in triplets if m[0] in KAZEPAI)
        kaze_head = head[0] in KAZEPAI if head else False
        if kaze_triplets == 4:
            yakuman_list.append(('대사희', 2))  # 더블 역만
        elif kaze_triplets == 3 and kaze_head:
            yakuman_list.append(('소사희', 1))

        # 자일색
        if all(is_honor(t) for t in tiles):
            yakuman_list.append(('자일색', 1))

        # 녹일색
        if all(is_green(t) for t in tiles):
            yakuman_list.append(('녹일색', 1))

        # 청노두
        if all(is_terminal(t) for t in tiles):
            yakuman_list.append(('청노두', 1))

        # 사암각 (4개 모두 암각)
        if len(triplets) == 4:
            yakuman_list.append(('사암각', 1))

    # 구련보등
    def is_churen(tiles):
        counts = count_tiles(tiles)
        for suit in ['m', 'p', 's']:
            suit_tiles = [t for t in tiles if t[1] == suit]
            if len(suit_tiles) == 14:
                needed = {f'1{suit}': 3, f'9{suit}': 3}
                for n in range(2, 9):
                    needed[f'{n}{suit}'] = 1
                ok = all(counts.get(t, 0) >= v for t, v in needed.items())
                if ok:
                    return True
        return False

    if decomp_type == 'standard' and is_churen(tiles):
        yakuman_list.append(('구련보등', 1))

    if yakuman_list:
        return {
            'yaku': [],
            'total_han': sum(m for _, m in yakuman_list) * 13,
            'is_yakuman': True,
            'yakuman_list': yakuman_list
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
        # 탕야오
        if all(not is_terminal_or_honor(t) for t in tiles):
            yaku_list.append(('탕야오', 1))

    elif decomp_type == 'standard':
        triplets = [m for t, m in zip(meld_types, melds) if t == 'triplet']
        sequences = [m for t, m in zip(meld_types, melds) if t == 'sequence']

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

        # 이페코 (멘젠 한정)
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

        # 삼색동순
        if _san_shoku_doujun(sequences):
            yaku_list.append(('삼색동순', 2))

        # 삼색동각
        if _san_shoku_doukou(triplets):
            yaku_list.append(('삼색동각', 2))

        # 이기도 (1~9 순자)
        if _ikkitsuukan(sequences):
            yaku_list.append(('이기도', 2))

        # 혼전대요구: 모든 면자+머리에 노두패 or 자패 포함
        if _honitsu_tanyao(tiles, melds, meld_types, head):
            yaku_list.append(('혼전대요구', 2))

        # 준전대요구 (혼전 + 자패 없음)
        if _junchantaiyao(tiles, melds, meld_types, head):
            yaku_list.append(('준전대요구', 3))

        # 산안커
        if len(triplets) == 3:
            yaku_list.append(('삼암각', 2))

        # 혼일색
        suits_used = set(t[1] for t in tiles if t[1] != 'z')
        has_honor = any(t[1] == 'z' for t in tiles)
        if len(suits_used) == 1 and has_honor:
            yaku_list.append(('혼일색', 3))

        # 청일색
        if len(suits_used) == 1 and not has_honor:
            yaku_list.append(('청일색', 6))

        # 토이토이
        if len(triplets) == 4:
            yaku_list.append(('토이토이', 2))

        # 친이쯔 (소삼원)
        sangenpai_heads = head[0] in SANGENPAI if head else False
        sangenpai_trips = sum(1 for m in triplets if m[0] in SANGENPAI)
        if sangenpai_trips == 2 and sangenpai_heads:
            yaku_list.append(('소삼원', 2))

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