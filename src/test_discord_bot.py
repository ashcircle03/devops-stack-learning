import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from discord.ext import commands
import os
import pytest
import datetime
import pytz

# Patch the Discord client before importing the bot
with patch('discord.Client.run'):
    with patch('discord.Client.login'):
        os.environ['BOT_TOKEN'] = 'test_token'
        from discord_bot import bot

class TestDiscordBot(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ctx = MagicMock()
        self.ctx.send = AsyncMock()

    def tearDown(self):
        self.loop.close()

    # 기존 add 명령어 테스트
    def test_add_command(self):
        async def run_test():
            await bot.get_command('add').callback(self.ctx, 2, 3)
            self.ctx.send.assert_called_once_with(5)
        self.loop.run_until_complete(run_test())

    # add 명령어 음수 테스트
    def test_add_command_negative(self):
        async def run_test():
            await bot.get_command('add').callback(self.ctx, -2, -3)
            self.ctx.send.assert_called_once_with(-5)
        self.loop.run_until_complete(run_test())

    # add 명령어 큰 숫자 테스트
    def test_add_command_large_numbers(self):
        async def run_test():
            await bot.get_command('add').callback(self.ctx, 999999, 999999)
            self.ctx.send.assert_called_once_with(1999998)
        self.loop.run_until_complete(run_test())

    # 기존 roll 명령어 테스트
    def test_roll_command(self):
        async def run_test():
            with patch('random.randint', return_value=4):
                await bot.get_command('roll').callback(self.ctx, '2d6')
                self.ctx.send.assert_called_once_with('4, 4')
        self.loop.run_until_complete(run_test())

    # roll 명령어 잘못된 형식 테스트
    def test_roll_command_invalid_format(self):
        async def run_test():
            await bot.get_command('roll').callback(self.ctx, 'invalid')
            self.ctx.send.assert_called_once_with('Format has to be in NdN!')
        self.loop.run_until_complete(run_test())

    # roll 명령어 음수 주사위 테스트
    def test_roll_command_negative_dice(self):
        async def run_test():
            await bot.get_command('roll').callback(self.ctx, '-1d6')
            self.ctx.send.assert_called_once_with('Format has to be in NdN!')
        self.loop.run_until_complete(run_test())

    # 기존 choose 명령어 테스트
    def test_choose_command(self):
        async def run_test():
            choices = ['option1', 'option2', 'option3']
            with patch('random.choice', return_value='option2'):
                await bot.get_command('choose').callback(self.ctx, *choices)
            self.ctx.send.assert_called_once_with('option2')
        self.loop.run_until_complete(run_test())

    # choose 명령어 단일 선택지 테스트
    def test_choose_command_single_option(self):
        async def run_test():
            choices = ['only_option']
            with patch('random.choice', return_value='only_option'):
                await bot.get_command('choose').callback(self.ctx, *choices)
            self.ctx.send.assert_called_once_with('only_option')
        self.loop.run_until_complete(run_test())

    # choose 명령어 한글 선택지 테스트
    def test_choose_command_korean(self):
        async def run_test():
            choices = ['김치', '비빔밥', '불고기']
            with patch('random.choice', return_value='김치'):
                await bot.get_command('choose').callback(self.ctx, *choices)
            self.ctx.send.assert_called_once_with('김치')
        self.loop.run_until_complete(run_test())

    # choose 명령어 빈 선택지 테스트
    def test_choose_command_empty_choices(self):
        async def run_test():
            with self.assertRaises(IndexError):
                await bot.get_command('choose').callback(self.ctx)
        self.loop.run_until_complete(run_test())

    # 기존 repeat 명령어 테스트
    def test_repeat_command(self):
        async def run_test():
            await bot.get_command('repeat').callback(self.ctx, 2, 'test')
            self.assertEqual(self.ctx.send.call_count, 2)
            self.ctx.send.assert_called_with('test')
        self.loop.run_until_complete(run_test())

    # repeat 명령어 최대값 테스트
    def test_repeat_command_max_times(self):
        async def run_test():
            await bot.get_command('repeat').callback(self.ctx, 5, 'test')
            self.assertEqual(self.ctx.send.call_count, 5)
        self.loop.run_until_complete(run_test())

    # repeat 명령어 한글 테스트
    def test_repeat_command_korean(self):
        async def run_test():
            await bot.get_command('repeat').callback(self.ctx, 2, '안녕하세요')
            self.assertEqual(self.ctx.send.call_count, 2)
            self.ctx.send.assert_called_with('안녕하세요')
        self.loop.run_until_complete(run_test())

    # repeat 명령어 음수 테스트
    def test_repeat_command_negative_times(self):
        async def run_test():
            await bot.get_command('repeat').callback(self.ctx, -1, 'test')
            self.ctx.send.assert_called_once_with('Number of repeats must be positive!')
        self.loop.run_until_complete(run_test())


    # 기존 joined 명령어 테스트
    def test_joined_command(self):
        async def run_test():
            with patch('discord.utils.format_dt') as mock_format_dt:
                member = MagicMock()
                member.name = 'TestUser'
                member.joined_at = '2023-01-01'
                formatted_date = '2023년 1월 1일'
                mock_format_dt.return_value = formatted_date
                await bot.get_command('joined').callback(self.ctx, member)
                self.ctx.send.assert_called_once_with(f'TestUser joined {formatted_date}')
        self.loop.run_until_complete(run_test())

    # joined 명령어 한글 이름 테스트
    def test_joined_command_korean_name(self):
        async def run_test():
            with patch('discord.utils.format_dt') as mock_format_dt:
                member = MagicMock()
                member.name = '홍길동'
                member.joined_at = '2023-01-01'
                formatted_date = '2023년 1월 1일'
                mock_format_dt.return_value = formatted_date
                await bot.get_command('joined').callback(self.ctx, member)
                self.ctx.send.assert_called_once_with(f'홍길동 joined {formatted_date}')
        self.loop.run_until_complete(run_test())

@pytest.mark.asyncio
async def test_time():
    # 가상의 컨텍스트 생성
    ctx = MockContext()
    
    # time 명령어 실행
    await bot.get_command('time').callback(ctx)
    
    # 응답 확인
    assert ctx.sent_message is not None
    assert '현재 한국 시간:' in ctx.sent_message
    
    # 시간 형식 확인
    time_str = ctx.sent_message.split('현재 한국 시간: ')[1]
    try:
        datetime.datetime.strptime(time_str.split(' KST')[0], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pytest.fail("Invalid time format")

if __name__ == '__main__':
    unittest.main()