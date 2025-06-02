# bot.py

import os
import json
import yt_dlp
import asyncio
import random
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message

# --- LOAD ENV VARS ---
load_dotenv()
API_ID = int(os.getenv("21737663")
API_HASH = os.getenv("1898391366167db54389f40cb6f37243")
BOT_TOKEN = os.getenv("8074621768:AAGcANPuhUJIq1_l3Nu-bfiPIXKrFkmZl9k")

RECENTS_FILE = "recents.json"
PLAYLISTS_FILE = "playlists.json"

app = Client("ytmusicbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- INIT DB ---
if not os.path.exists(RECENTS_FILE):
    with open(RECENTS_FILE, "w") as f: json.dump({}, f)
if not os.path.exists(PLAYLISTS_FILE):
    with open(PLAYLISTS_FILE, "w") as f: json.dump({}, f)

def load_json(file):
    with open(file) as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# --- DOWNLOAD AUDIO ---
async def download_audio(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': 'downloaded.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        title = info.get("title")
        filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
    return filename, title, info.get("webpage_url"), info.get("related_videos", [])

# --- COMMANDS ---
@app.on_message(filters.command("play"))
async def play(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /play [song name or YouTube link]")

    query = " ".join(msg.command[1:])
    m = await msg.reply("Searching and downloading...")
    filename, title, url, related = await download_audio(query)

    await msg.reply_audio(audio=filename, title=title, caption=f"Now playing: {title}\n🔗 {url}")
    os.remove(filename)

    # Update recents
    recents = load_json(RECENTS_FILE)
    uid = str(msg.from_user.id)
    recents.setdefault(uid, []).insert(0, {'title': title, 'url': url})
    recents[uid] = recents[uid][:10]
    save_json(RECENTS_FILE, recents)

    # Cache similar
    app.user_cache[uid] = related

@app.on_message(filters.command("recent"))
async def recent(_, msg: Message):
    uid = str(msg.from_user.id)
    recents = load_json(RECENTS_FILE).get(uid, [])
    if not recents:
        return await msg.reply("No recent songs found.")
    txt = "\n".join([f"{i+1}. [{r['title']}]({r['url']})" for i, r in enumerate(recents)])
    await msg.reply(txt, disable_web_page_preview=True)

@app.on_message(filters.command("skip"))
async def skip(_, msg: Message):
    uid = str(msg.from_user.id)
    related = getattr(app, 'user_cache', {}).get(uid, [])
    if not related:
        return await msg.reply("No similar songs cached. Play a song first.")
    next_url = f"https://www.youtube.com/watch?v={random.choice(related)['id']}"
    filename, title, url, _ = await download_audio(next_url)
    await msg.reply_audio(audio=filename, title=title, caption=f"Next up: {title}\n🔗 {url}")
    os.remove(filename)

@app.on_message(filters.command("addtoplaylist"))
async def add_to_playlist(_, msg: Message):
    uid = str(msg.from_user.id)
    recents = load_json(RECENTS_FILE).get(uid, [])
    if not recents:
        return await msg.reply("Play a song first to add to playlist.")
    playlists = load_json(PLAYLISTS_FILE)
    playlists.setdefault(uid, []).append(recents[0])
    save_json(PLAYLISTS_FILE, playlists)
    await msg.reply("Added to your playlist.")

@app.on_message(filters.command("playlist"))
async def show_playlist(_, msg: Message):
    uid = str(msg.from_user.id)
    playlist = load_json(PLAYLISTS_FILE).get(uid, [])
    if not playlist:
        return await msg.reply("Your playlist is empty.")
    txt = "\n".join([f"{i+1}. [{r['title']}]({r['url']})" for i, r in enumerate(playlist)])
    await msg.reply(txt, disable_web_page_preview=True)

# Init user cache for related tracks
app.user_cache = {}

# --- RUN ---
app.run()
    
