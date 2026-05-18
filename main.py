import sys
import types

# ==================== CRITICAL PATCH ====================
class DummyAudioop:
    error = Exception
    def mul(self, cp, size, factor): return b''
    def max(self, cp, size): return 0
    def lin2lin(self, fragment, width, newwidth): return b''
    def ratecv(self, fragment, width, nchannels, inrate, outrate, state): return (b'', None)
    def ulaw2lin(self, fragment, width): return b''
    def lin2ulaw(self, fragment, width): return b''
    def alaw2lin(self, fragment, width): return b''
    def lin2alaw(self, fragment, width): return b''

sys.modules['audioop'] = DummyAudioop()
# ========================================================

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

    @tasks.loop(seconds=15)
    async def check_voice_status(self):
        if not active_accounts:
            return

        for acc in active_accounts:
            token = acc['token']
            channel_id = acc['channel_id']
            guild_id = acc.get('guild_id') # جلب أيدي السيرفر إذا توفر
            
            headers = {
                "Authorization": token,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            try:
                # خطوة 1: جلب معلومات الروم الصوتي لمعرفة أيدي السيرفر (Guild ID) تلقائياً
                if not guild_id:
                    ch_res = requests.get(f"https://discord.com/api/v9/channels/{channel_id}", headers=headers)
                    if ch_res.status_code == 200:
                        guild_id = ch_res.json().get('guild_id')
                        acc['guild_id'] = guild_id # حفظه عشان ما يتكرر الطلب
                
                if not guild_id:
                    print(f"[-] Could not find Guild ID for channel {channel_id}")
                    continue

                # خطوة 2: إرسال طلب الاتصال الصوتي الفعلي (الـ Endpoint الصحيح للحسابات الشخصية)
                payload = {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "self_mute": True,
                    "self_deaf": True,
                    "self_video": False
                }
                
                # إرسال الطلب عبر الـ Gateway/API الخاص بالحساب ومحاكاة الدخول
                connect_url = f"https://discord.com/api/v9/guilds/{guild_id}/voice-states/%40me"
                response = requests.patch(connect_url, headers=headers, json=payload)
                
                if response.status_code in [200, 204]:
                    print(f"[+] Account [{token[:15]}...] Successfully joined/verified in Voice Channel.")
                elif response.status_code == 429:
                    retry_after = response.json().get('retry_after', 5)
                    print(f"[!] Rate limited. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"[-] Failed to join. Status Code: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"[X] Error executing request: {e}")
            
            await asyncio.sleep(random.uniform(2.0, 5.0))

    @check_voice_status.before_loop
    async def before_check(self):
        await self.wait_until_ready()

class AccountInputModal(discord.ui.Modal, title="Account Information"):
    token_input = discord.ui.TextInput(
        label="Discord Account Token", 
        placeholder="Enter user token here...", 
        required=True
    )
    channel_id_input = discord.ui.TextInput(
        label="Voice Channel ID", 
        placeholder="Enter voice channel ID here...", 
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token_input.value.strip()
        channel_id = self.channel_id_input.value.strip()
        account_data = {'token': token, 'channel_id': channel_id}
        
        if account_data not in active_accounts:
            active_accounts.append(account_data)
            await interaction.response.send_message("✅ الحساب قيد الدخول الآن، انتظر ثواني ويدخل الروم!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ هذا الحساب مضاف بالفعل سابقاً.", ephemeral=True)

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
