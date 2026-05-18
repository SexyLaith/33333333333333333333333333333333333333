import sys
import types

# ==================== PYTHON 3.13 AUDIOOP PATCH ====================
# هذي الخدعة توهم بايثون 3.13 أن مكتبة audioop موجودة لتفادي انهيار مكتبة ديسكورد
if 'audioop' not in sys.modules:
    dummy_audioop = types.ModuleType('audioop')
    dummy_audioop.error = Exception
    # إضافة الدوال الأساسية التي تبحث عنها مكتبة discord.py فارغة
    dummy_audioop.mul = lambda cp, size, factor: b''
    dummy_audioop.max = lambda cp, size: 0
    sys.modules['audioop'] = dummy_audioop
# ===================================================================

import discord
from discord import app_commands
from discord.ext import tasks
import requests
import asyncio
import random
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

active_accounts = []

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.check_voice_status.start()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.tree.sync()

    @tasks.loop(seconds=20)
    async def check_voice_status(self):
        if not active_accounts:
            return

        for acc in active_accounts:
            token = acc['token']
            channel_id = acc['channel_id']
            
            headers = {
                "Authorization": token,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            try:
                check_url = f"https://discord.com/api/v9/channels/{channel_id}"
                requests.get(check_url, headers=headers)
                
                payload = {
                    "jump_to_voice_channel": True,
                    "deaf": True,
                    "mute": True,
                    "self_deaf": True,
                    "self_mute": True
                }
                
                connect_url = f"https://discord.com/api/v9/channels/{channel_id}/voice-states/%40me"
                response = requests.patch(connect_url, headers=headers, json=payload)
                
                if response.status_code == 204:
                    print(f"Account [{token[:12]}...] is connected.")
                elif response.status_code == 429:
                    retry_after = response.json().get('retry_after', 5)
                    print(f"Rate limited. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    
            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(random.uniform(5.0, 15.0))

    @check_voice_status.before_loop
    async def before_check(self):
        await self.wait_until_ready()

class AccountInputModal(discord.ui.Modal, title="Account Information"):
    token_input = discord.ui.TextInput(
        label="Discord Account Token", 
        placeholder="Enter token here...", 
        required=True
    )
    channel_id_input = discord.ui.TextInput(
        label="Voice Channel ID", 
        placeholder="Enter channel ID here...", 
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token_input.value.strip()
        channel_id = self.channel_id_input.value.strip()
        account_data = {'token': token, 'channel_id': channel_id}
        
        if account_data not in active_accounts:
            active_accounts.append(account_data)
            await interaction.response.send_message("Success", ephemeral=True)
        else:
            await interaction.response.send_message("Already added", ephemeral=True)

class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, custom_id="start_btn")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AccountInputModal())

bot = MyBot()

@bot.tree.command(name="start", description="Start AFK system")
async def start_command(interaction: discord.Interaction):
    await interaction.response.send_message("Click the button below to start:", view=StartView())

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
