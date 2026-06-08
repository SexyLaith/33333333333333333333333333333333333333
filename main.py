import sys
import types

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

import asyncio
import json
import os
from flask import Flask
from threading import Thread
import websockets

app = Flask('')

@app.route('/')
def home():
    return "AFK System is Live 24/7"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

TOKEN = os.getenv("ACCOUNT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

class DiscordVoiceAFK:
    def __init__(self, token, guild_id, channel_id):
        self.token = token
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
        self.heartbeat_interval = None
        self.sequence = None
        self.user_id = None  

    async def send_heartbeat(self, ws):
        while True:
            if self.heartbeat_interval:
                await asyncio.sleep(self.heartbeat_interval / 1000)
                heartbeat_payload = {"op": 1, "d": self.sequence}
                try:
                    await ws.send(json.dumps(heartbeat_payload))
                except:
                    break
            else:
                await asyncio.sleep(1)

    async def join_voice(self, ws):
        voice_state_payload = {
            "op": 4,
            "d": {
                "guild_id": self.guild_id,
                "channel_id": self.channel_id,
                "self_mute": True,
                "self_deaf": True,
                "self_video": False
            }
        }
        await ws.send(json.dumps(voice_state_payload))

    async def start(self):
        print("[*] Connecting to Discord Gateway via Websocket...")
        
        async for ws in websockets.connect(self.ws_url, max_size=None):
            try:
                hello_msg = await ws.recv()
                hello_data = json.loads(hello_msg)
                
                if hello_data['op'] == 10:  
                    self.heartbeat_interval = hello_data['d']['heartbeat_interval']
                    asyncio.create_task(self.send_heartbeat(ws))
                
                identify_payload = {
                    "op": 2,
                    "d": {
                        "token": self.token,
                        "capabilities": 8189,
                        "properties": {
                            "os": "Android",
                            "browser": "Discord Android",
                            "device": "phone"
                        },
                        "presence": {
                            "status": "dnd",
                            "since": 0,
                            "activities": [],
                            "afk": False
                        },
                        "compress": False
                    }
                }
                await ws.send(json.dumps(identify_payload))
                
                await asyncio.sleep(1.5)
                await self.join_voice(ws)
                print(f"[+] Successfully connected! Account is now AFK in Voice Channel: {self.channel_id}")

                async_messages = ws
                async for message in async_messages:
                    data = json.loads(message)
                    
                    if data.get('s'):
                        self.sequence = data['s']
                        
                    op = data.get('op')
                    t = data.get('t')
                    d = data.get('d', {})

                    if t == "READY":
                        self.user_id = d.get('user', {}).get('id')

                    elif t == "VOICE_STATE_UPDATE":
                        if self.user_id and d.get('user_id') == self.user_id:
                            current_channel = d.get('channel_id')
                            if current_channel != self.channel_id:
                                print("[!] Detected kick or leave! Rejoining voice channel instantly...")
                                await self.join_voice(ws)

                    if op == 7:
                        print("[!] Discord requested reconnect. Reconnecting...")
                        break

            except websockets.ConnectionClosed:
                print("[!] Connection closed. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                print(f"[X] Error: {e}")
                await asyncio.sleep(5)
                continue

if __name__ == "__main__":
    if not TOKEN or not GUILD_ID or not CHANNEL_ID:
        print("[X] Critical Error: Missing Environment Variables (ACCOUNT_TOKEN, GUILD_ID, CHANNEL_ID) in Host Settings!")
        sys.exit(1)
        
    keep_alive()
    
    asyncio.run(DiscordVoiceAFK(TOKEN, GUILD_ID, CHANNEL_ID).start())
