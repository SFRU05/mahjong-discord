"""
리치 마작 점수 퀴즈 디스코드 봇 Cog
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Optional
import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tiles import tile_to_emoji, tiles_to_str, next_tile, ALL_TILES, ZI_NAMES
from mahjongquiz.hand_generator import generate_random_winning_hand
from mahjongquiz.yaku_calculator import calculate_yaku
from mahjongquiz.fu_calculator import calculate_fu, calculate_fu_with_details
from mahjongquiz.score_calculator import calculate_score, level_name


# 진행 중인 퀴즈 세션 저장 {channel_id: QuizSession}
active_sessions: dict = {}


class QuizSession:
    def __init__(self, hand_info, extra, dora_tiles, ura_dora_tiles,
                 yaku_result, fu, score_result, is_dealer, honba, fu_details=None):
        self.hand_info = hand_info
        self.extra = extra
        self.dora_tiles = dora_tiles
        self.ura_dora_tiles = ura_dora_tiles
        self.yaku_result = yaku_result
        self.fu = fu
        self.fu_details = fu_details or {'details': []}
        self.score_result = score_result
        self.is_dealer = is_dealer
        self.honba = honba
        self.answered = False

    def correct_answer(self) -> int:
        return self.score_result['total']


def generate_dora(count: int = 1) -> list:
    """도라 표시패 생성 (실제 도라는 다음 패)"""
    return random.choices(ALL_TILES, k=count)


def make_quiz(is_dealer: bool = None, honba: int = 0) -> Optional[QuizSession]:
    if is_dealer is None:
        is_dealer = random.choice([True, False])

    seat_wind = '1z' if is_dealer else random.choice(['2z', '3z', '4z'])
    round_wind = random.choice(['1z', '2z'])
    
    # 동풍 장에서 자풍이 동이면 반드시 오야(동가)여야 함
    if round_wind == '1z' and seat_wind == '1z':
        is_dealer = True

    # 추가 조건 랜덤 결정
    is_tsumo = random.choice([True, False])
    riichi = random.choice([True, True, False])  # 리치 가중치 높임
    double_riichi = riichi and random.random() < 0.1
    ippatsu = riichi and random.random() < 0.25
    haitei = is_tsumo and not riichi and random.random() < 0.15
    houtei = not is_tsumo and not riichi and random.random() < 0.15
    rinshan = is_tsumo and random.random() < 0.05
    chankan = not is_tsumo and random.random() < 0.05

    extra = {
        'riichi': riichi and not double_riichi,
        'double_riichi': double_riichi,
        'ippatsu': ippatsu,
        'haitei': haitei,
        'houtei': houtei,
        'rinshan': rinshan,
        'chankan': chankan,
    }

    hand_info = generate_random_winning_hand(
        seat_wind=seat_wind,
        round_wind=round_wind,
        tsumo=is_tsumo,
    )
    if not hand_info:
        return None

    # 도라 (표시패 1~3장)
    dora_count = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
    dora_indicators = generate_dora(dora_count)
    actual_doras = [next_tile(t) for t in dora_indicators]

    # 뒷도라 (리치 시)
    ura_count = 0
    ura_indicators = []
    actual_uras = []
    if riichi or double_riichi:
        ura_count = random.choices([0, 1, 2], weights=[40, 45, 15])[0]
        ura_indicators = generate_dora(ura_count)
        actual_uras = [next_tile(t) for t in ura_indicators]

    # 도라 한수 계산
    tiles = hand_info['tiles']
    dora_han = sum(tiles.count(d) for d in actual_doras)
    ura_han = sum(tiles.count(u) for u in actual_uras)

    # 역 계산
    yaku_result = calculate_yaku(hand_info, extra)

    # 역 없으면 재시도 신호
    if not yaku_result['is_yakuman'] and yaku_result['total_han'] == 0:
        return None

     # 도라 추가
    total_han = yaku_result['total_han'] + dora_han + ura_han

    # 부수 계산 (상세 정보 포함)
    fu_details = calculate_fu_with_details(hand_info, yaku_result, extra)
    fu = fu_details['fu']

    # 점수 계산
    score_result = calculate_score(fu, total_han, is_tsumo, is_dealer, honba)

    return QuizSession(
        hand_info=hand_info,
        extra=extra,
        dora_tiles=list(zip(dora_indicators, actual_doras)),
        ura_dora_tiles=list(zip(ura_indicators, actual_uras)),
        yaku_result=yaku_result,
        fu=fu,
        score_result=score_result,
        is_dealer=is_dealer,
        honba=honba,
        fu_details=fu_details,
    )


def build_quiz_embed(session: QuizSession) -> discord.Embed:
    hand_info = session.hand_info
    extra = session.extra
    tiles = hand_info['tiles']
    win_tile = hand_info['win_tile']
    decomp_type = hand_info['decomp_type']
    is_tsumo = hand_info['is_tsumo']
    seat_wind = hand_info['seat_wind']
    round_wind = hand_info['round_wind']

    embed = discord.Embed(
        title='🀄 리치 마작 점수 퀴즈!',
        color=0xE63946,
    )

    # 상황 정보
    wind_names = {'1z':'동','2z':'남','3z':'서','4z':'북'}
    situation_parts = [
        f"**장**: {wind_names.get(round_wind, '?')}장",
        f"**자풍**: {wind_names.get(seat_wind, '?')}",
        f"**{'동가(친)' if session.is_dealer else '비친'}**",
        f"**본장**: {session.honba}본",
    ]
    embed.add_field(name='📋 상황', value=' | '.join(situation_parts), inline=False)

    # 패 표시
    if decomp_type == 'chiitoitsu':
        pairs = []
        counts = {}
        for t in sorted(tiles):
            counts[t] = counts.get(t, 0) + 1
        tile_str = tiles_to_str(sorted(tiles))
        embed.add_field(name='🀄 손패 (치또이쯔)', value=tile_str, inline=False)
    else:
        head = hand_info['head']
        melds = hand_info['melds']

        meld_strs = []
        for meld in melds:
            meld_strs.append(tiles_to_str(list(meld)))

        hand_display = (
            f"**머리**: {tiles_to_str(list(head))}\n"
            f"**몸통**: " + '  '.join(meld_strs)
        )
        embed.add_field(name='🀄 손패', value=hand_display, inline=False)

    # 화료패
    win_method = '쯔모' if is_tsumo else '론'
    embed.add_field(
        name=f'🎯 화료패 ({win_method})',
        value=tile_to_emoji(win_tile),
        inline=True
    )

    # 추가 조건
    conditions = []
    if extra.get('double_riichi'):
        conditions.append('더블리치')
    elif extra.get('riichi'):
        conditions.append('리치')
    if extra.get('ippatsu'):
        conditions.append('일발')
    if extra.get('haitei'):
        conditions.append('해저로어')
    if extra.get('houtei'):
        conditions.append('하저로월')
    if extra.get('rinshan'):
        conditions.append('영상개화')
    if extra.get('chankan'):
        conditions.append('창깡')

    if conditions:
        embed.add_field(
            name='⚡ 특수 조건',
            value=' / '.join(conditions),
            inline=True
        )

    # 도라 표시
    dora_display = []
    for indicator, actual in session.dora_tiles:
        dora_display.append(f"{tile_to_emoji(indicator)}→{tile_to_emoji(actual)}")

    if dora_display:
        embed.add_field(
            name='🌟 도라 (표시패→도라)',
            value='  '.join(dora_display),
            inline=False
        )

    # 뒷도라 (리치 시 표시 - 퀴즈에서는 힌트로 공개)
    if session.ura_dora_tiles:
        ura_display = []
        for indicator, actual in session.ura_dora_tiles:
            ura_display.append(f"{tile_to_emoji(indicator)}→{tile_to_emoji(actual)}")
        embed.add_field(
            name='✨ 뒷도라 (표시패→뒷도라)',
            value='  '.join(ura_display),
            inline=False
        )

    embed.set_footer(text='💬 획득 점수를 숫자로 입력하세요! (예: 8000)')
    return embed


def build_answer_embed(session: QuizSession) -> discord.Embed:
    yaku = session.yaku_result
    score = session.score_result
    fu = session.fu
    hand_info = session.hand_info

    level = score.get('level')
    level_str = f' ({level_name(level)})' if level else ''

    embed = discord.Embed(
        title='📊 정답 해설',
        color=0x2ECC71,
    )

    # 역 목록
    if yaku['is_yakuman']:
        yaku_str = '\n'.join(f"• {n} (×{m})" for n, m in yaku['yakuman_list'])
        embed.add_field(name='🏆 역만!', value=yaku_str, inline=False)
    else:
        yaku_str = '\n'.join(f"• {n}: {h}판" for n, h in yaku['yaku'])
        if not yaku_str:
            yaku_str = '(역 없음)'
        embed.add_field(name='📜 역', value=yaku_str, inline=True)

    # 도라 한수
    tiles = hand_info['tiles']
    dora_han = sum(tiles.count(a) for _, a in session.dora_tiles)
    ura_han = sum(tiles.count(a) for _, a in session.ura_dora_tiles)

    if dora_han or ura_han:
        dora_str = ''
        if dora_han:
            dora_str += f'• 도라: {dora_han}판\n'
        if ura_han:
            dora_str += f'• 뒷도라: {ura_han}판'
        embed.add_field(name='🌟 도라', value=dora_str.strip(), inline=True)

    total_han = yaku['total_han'] + dora_han + ura_han

    # 부수/한수
    if not yaku['is_yakuman']:
        embed.add_field(
            name='🔢 부수 / 한수',
            value=f'{fu}부 {total_han}판{level_str}',
            inline=False
        )

    # 점수 표시 (오야 여부에 따라)
    score_display = f"**{score['total']:,}점**"
    
    # 오야(동가)인 경우 추가 표시
    if session.is_dealer:
        payment_details = score['payment']
        if 'ALL' not in payment_details:
            # 쯔모일 경우
            if 'tsumo_each' in score:
                score_display += f"\n({score['tsumo_each']:,} ALL)"
            # 론일 경우
            elif 'ron' in score:
                score_display += f"\n({score['ron']:,} ALL)"
    
    embed.add_field(
        name='💰 정답 점수',
        value=f"{score_display}\n{score['payment']}",
        inline=False
    )

    return embed


def build_fu_details_embed(session: QuizSession) -> discord.Embed:
    """부수 계산 상세 설명 embed"""
    fu_details = session.fu_details
    yaku = session.yaku_result
    fu = session.fu
    score = session.score_result
    
    level = score.get('level')
    level_str = f' ({level_name(level)})' if level else ''
    
    embed = discord.Embed(
        title='📊 부수 계산 상세',
        color=0x3498db,
    )
    
    # 부수 계산 내역
    if fu_details.get('details'):
        details_text = ""
        for desc, fu_value in fu_details['details']:
            if fu_value == 0:
                details_text += f"• {desc}: {fu_value}부\n"
            else:
                details_text += f"• {desc}: {fu_value}부\n"
        
        embed.add_field(name='🔢 부수 계산', value=details_text.strip(), inline=False)
    
    # 최종 부수
    base_fu = fu_details.get('base_fu', fu)
    if base_fu != fu:
        embed.add_field(
            name='🧮 절상',
            value=f'{base_fu}부 → **{fu}부** (10단위 절상)',
            inline=False
        )
    else:
        embed.add_field(
            name='🧮 최종 부수',
            value=f'**{fu}부**',
            inline=False
        )
    
    # 총 한수와 점수
    tiles = session.hand_info['tiles']
    dora_han = sum(tiles.count(a) for _, a in session.dora_tiles)
    ura_han = sum(tiles.count(a) for _, a in session.ura_dora_tiles)
    total_han = yaku['total_han'] + dora_han + ura_han
    
    points_str = f"{fu}부 × {total_han}판{level_str}\n"
    points_str += f"→ **{score['total']:,}점**"
    
    embed.add_field(
        name='💰 점수',
        value=points_str,
        inline=False
    )
    
    return embed


class QuizCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='퀴즈', description='리치 마작 점수 퀴즈를 시작합니다.')
    @app_commands.describe(
        is_dealer='동가(친) 여부 (기본: 랜덤)',
        honba='본장 수 (기본: 0)',
    )
    async def quiz(
        self,
        interaction: discord.Interaction,
        is_dealer: Optional[bool] = None,
        honba: Optional[int] = 0,
    ):
        channel_id = interaction.channel_id

        if channel_id in active_sessions:
            await interaction.response.send_message(
                '⚠️ 이미 진행 중인 퀴즈가 있습니다! 먼저 `/정답`으로 확인하거나 `/포기`하세요.',
                ephemeral=True
            )
            return

        await interaction.response.defer()

        session = None
        for _ in range(20):
            session = make_quiz(is_dealer=is_dealer, honba=honba or 0)
            if session:
                break

        if not session:
            await interaction.followup.send('❌ 패 생성에 실패했습니다. 다시 시도해 주세요.')
            return

        active_sessions[channel_id] = session
        embed = build_quiz_embed(session)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='정답', description='현재 퀴즈의 정답을 확인합니다.')
    async def show_answer(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        session = active_sessions.get(channel_id)

        if not session:
            await interaction.response.send_message(
                '❌ 진행 중인 퀴즈가 없습니다. `/퀴즈`로 시작하세요!',
                ephemeral=True
            )
            return

        del active_sessions[channel_id]
        answer_embed = build_answer_embed(session)
        answer_embed.title = '📖 정답 공개 (포기)'
        fu_embed = build_fu_details_embed(session)
        await interaction.response.send_message(embeds=[answer_embed, fu_embed])

    @app_commands.command(name='포기', description='현재 퀴즈를 포기하고 정답을 봅니다.')
    async def give_up(self, interaction: discord.Interaction):
        await self.show_answer(interaction)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """메시지로 점수 입력 처리"""
        if message.author.bot:
            return

        channel_id = message.channel.id
        session = active_sessions.get(channel_id)
        if not session or session.answered:
            return

        # 숫자만 입력한 경우
        content = message.content.strip().replace(',', '').replace(' ', '')
        if not content.isdigit():
            return

        user_answer = int(content)
        correct = session.correct_answer()

        session.answered = True
        del active_sessions[channel_id]

        answer_embed = build_answer_embed(session)
        fu_embed = build_fu_details_embed(session)

        if user_answer == correct:
            result_embed = discord.Embed(
                title='🎉 정답!',
                description=f'{message.author.mention} 정확합니다! **{correct:,}점**',
                color=0x2ECC71,
            )
        else:
            diff = abs(user_answer - correct)
            result_embed = discord.Embed(
                title='❌ 오답',
                description=(
                    f'{message.author.mention} 아쉽습니다!\n'
                    f'입력: **{user_answer:,}점** / 정답: **{correct:,}점**\n'
                    f'차이: {diff:,}점'
                ),
                color=0xE74C3C,
            )

        await message.channel.send(embeds=[result_embed, answer_embed, fu_embed])


async def setup(bot: commands.Bot):
    await bot.add_cog(QuizCog(bot))



