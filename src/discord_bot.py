import os
import discord
from discord.ext import commands, tasks
import random
import datetime
import pytz
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# 프로메테우스 메트릭 정의
COMMAND_COUNTER = Counter('discord_bot_commands_total', 'Total number of commands executed', ['command'])
MESSAGE_LATENCY = Histogram('discord_bot_message_latency_seconds', 'Message processing latency')

# Slack 로깅 설정
# 환경 변수에서 Slack 토큰 가져오기 (없으면 None)
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#discord-bot-logs')

# 로깅 설정
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)

# 콘솔 핸들러 추가
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Slack 클라이언트 초기화 (토큰이 설정된 경우에만)
slack_client = None
if SLACK_BOT_TOKEN and SLACK_CHANNEL:
    try:
        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        logger.info("Slack 클라이언트가 성공적으로 초기화되었습니다.")
    except Exception as e:
        logger.error(f"Slack 클라이언트 초기화 중 오류 발생: {str(e)}")
else:
    logger.warning("SLACK_BOT_TOKEN 또는 SLACK_CHANNEL이 설정되지 않아 Slack 알림이 비활성화됩니다.")

# Slack으로 메시지 보내는 함수
async def send_to_slack(message, level='info'):
    if not slack_client:
        return
    
    # 로그 레벨에 따른 이모지 설정
    emoji = {
        'info': ':information_source:',
        'warning': ':warning:',
        'error': ':x:',
        'success': ':white_check_mark:'
    }.get(level, ':information_source:')
    
    try:
        # Slack에 메시지 전송 (비동기 호출)
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"{emoji} {message}"
        )
        logger.info(f"Slack에 메시지 전송 성공: {level}")
    except SlackApiError as e:
        logger.error(f"Slack에 메시지를 보내는 중 오류 발생: {e.response['error'] if hasattr(e, 'response') else str(e)}")


# 봇 토큰 환경 변수에서 가져오기
TOKEN = os.environ['BOT_TOKEN']

# 봇 설명
description = '''Discord 유틸리티 봇'''

# 봇 권한 설정
intents = discord.Intents.default()
intents.members = True  # 멤버 관련 권한 활성화
intents.message_content = True  # 메시지 내용 읽기 권한 활성화

# 봇 객체 생성 (명령어 접두사: ?)
bot = commands.Bot(command_prefix='?', description=description, intents=intents)
# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    # 프로메테우스 메트릭 서버 시작
    start_http_server(8000)
    
    # 로그 출력
    logger.info(f"디스코드 봇 시작 (ID: {bot.user.id})")
    
    # Slack으로 봇 시작 알림 보내기
    try:
        korea_time = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
        startup_message = f"""🚀 *디스코드 봇이 시작되었습니다!*
• 버전: `32`
• 서버 시간: `{korea_time}`
• 사용자 수: `{len(bot.users)}`
• 서버 수: `{len(bot.guilds)}`"""
        
        await send_to_slack(startup_message, level='success')
        logger.info("봇 시작 알림을 Slack으로 전송했습니다.")
    except Exception as e:
        logger.error(f"Slack으로 시작 알림을 보내는 중 오류 발생: {str(e)}")

# 명령어 실행 전/후 처리
@bot.before_invoke
async def before_invoke(ctx):
    # discord.ext.tasks를 사용하여 시간 측정
    ctx._start_time = datetime.datetime.now()

@bot.after_invoke
async def after_invoke(ctx):
    # discord.ext.tasks를 사용하여 시간 측정
    if hasattr(ctx, '_start_time'):
        end_time = datetime.datetime.now()
        start_time = getattr(ctx, '_start_time')
        latency = (end_time - start_time).total_seconds()
        # 지연 시간 측정 및 프로메테우스 메트릭 갱신
        MESSAGE_LATENCY.observe(latency)
        log_message = f'명령어 {ctx.command} 실행 완료 - 지연 시간: {latency:.4f}초'
        print(log_message)
        
        # Slack으로 명령어 실행 로그 전송 (지연 시간이 1초 이상인 경우에만)
        if latency > 1.0:
            await send_to_slack(
                f'⚠️ 느린 명령어 감지: `{ctx.command}` - 지연 시간: {latency:.4f}초\n'
                f'사용자: {ctx.author.name} ({ctx.author.id})\n'
                f'서버: {ctx.guild.name if ctx.guild else "DM"}\n'
                f'채널: {ctx.channel.name if hasattr(ctx.channel, "name") else "DM"}',
                level='warning'
            )
        COMMAND_COUNTER.labels(command=ctx.command.name).inc()

# 두 숫자를 더하는 명령어
@bot.command()
async def add(ctx, left, right):
    """두 숫자를 더합니다. 사용법: !add <숫자1> <숫자2>"""
    try:
        left_num = int(left)
        right_num = int(right)
        await ctx.send(f"{left_num} + {right_num} = {left_num + right_num}")
    except ValueError:
        await ctx.send("올바른 숫자를 입력해주세요! 예: `!add 10 20`")
# 주사위를 굴리는 명령어 (NdN 형식: N개의 N면체 주사위)
@bot.command()
async def roll(ctx, dice: str):
    """주사위를 굴립니다. 형식: NdN (예: 2d6)"""
    try:
        rolls, limit = map(int, dice.split('d'))
        if rolls <= 0 or limit <= 0 or rolls > 100:
            await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
            return
        results = [random.randint(1, limit) for r in range(rolls)]
        await ctx.send(', '.join(str(r) for r in results))
    except ValueError:
        await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
# 여러 선택지 중 하나를 무작위로 선택하는 명령어
@bot.command()
async def choose(ctx, *choices: str):
    """여러 선택지 중 하나를 무작위로 선택합니다."""
    if not choices:
        await ctx.send('선택지를 입력해주세요!')
        return
    await ctx.send(random.choice(choices))
# 메시지를 지정된 횟수만큼 반복하는 명령어
@bot.command()
async def repeat(ctx, times, content='repeating...'):
    """메시지를 여러 번 반복합니다. 사용법: !repeat <횟수> [메시지]"""
    try:
        # 숫자로 변환 시도
        times_int = int(times)
        
        # 횟수 유효성 검사
        if times_int <= 0:
            await ctx.send('반복 횟수는 1 이상이어야 합니다!')
            return
        if times_int > 10:  # 너무 많은 반복을 방지
            await ctx.send('반복 횟수는 최대 10회까지 가능합니다.')
            return
            
        # 메시지 전송
        for i in range(times_int):
            await ctx.send(content)
            
    except ValueError:
        await ctx.send('반복 횟수는 숫자로 입력해주세요! 예: `!repeat 3 안녕하세요`')
# 멤버의 서버 참가일을 보여주는 명령어
@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')
# 'cool' 명령어 그룹 생성
@bot.group()
async def cool(ctx):
    """Says if a user is cool.
    In reality this just checks if a subcommand is being invoked.
    """
    # 하위 명령어가 없을 경우
    if ctx.invoked_subcommand is None:
        await ctx.send(f'No, {ctx.subcommand_passed} is not cool')


# 'cool' 그룹의 'bot' 하위 명령어
@cool.command(name='bot')
async def _bot(ctx):
    """Is the bot cool?"""
    await ctx.send('Yes, the bot is cool.')


# 현재 시간을 보여주는 명령어
@bot.command()
async def time(ctx):
    """현재 한국 시간을 보여줍니다."""
    korea_tz = pytz.timezone('Asia/Seoul')
    current_time = datetime.datetime.now(korea_tz)
    await ctx.send(f'현재 한국 시간: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')


# 음성 채널에 참가하는 명령어
@bot.command()
async def join(ctx):
    """봇을 음성 채널에 참가시킵니다."""
    if ctx.author.voice is None:
        await ctx.send("먼저 음성 채널에 참가해주세요!")
        return
    
    await ctx.send("이 명령어는 더 이상 지원되지 않습니다. 음악 관련 기능이 제거되었습니다.")
    # Slack에 로그 전송
    await send_to_slack(f"사용자 {ctx.author.name}이 제거된 join 명령어를 사용했습니다.", level='warning')


# 음성 채널 관련 안내 명령어 (이전 명령어 대체)
@bot.command(aliases=["dc"])
async def disconnect(ctx):
    """이전 음성 채널 연결 해제 명령어 (현재는 지원하지 않음)"""
    await ctx.send("이 명령어는 더 이상 지원되지 않습니다. 음악 관련 기능이 제거되었습니다.")
    # Slack에 로그 전송
    await send_to_slack(f"사용자 {ctx.author.name}이 제거된 disconnect 명령어를 사용했습니다.", level='warning')


# 봇 실행 (직접 실행될 때만)
if __name__ == '__main__':
    bot.run(TOKEN)