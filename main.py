#!/usr/bin/env python3
"""
VIRAL YOUTUBE SHORTS GENERATOR - FINAL STABLE VERSION
GitHub Actions ile otomatik calisacak sekilde hazirlanmistir.

Gerekli GitHub Secrets:
- PEXELS_API_KEY
- YOUTUBE_REFRESH_TOKEN
- CLIENT_SECRETS_JSON
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
import time
import traceback
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")

if not PEXELS_API_KEY:
    sys.exit("PEXELS_API_KEY tanimli degil.")
if not YOUTUBE_REFRESH_TOKEN:
    sys.exit("YOUTUBE_REFRESH_TOKEN tanimli degil.")

CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_CATEGORY_ID = "22"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

import edge_tts
import g4f
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.audio.fx.all import audio_loop, volumex
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
)
from moviepy.video.fx.all import crop

OUTPUT_VIDEO = "final_shorts.mp4"
VOICEOVER_FILE = "voiceover.mp3"
BACKGROUND_FILE = "background_video.mp4"
VIDEO_SIZE = (1080, 1920)
DEFAULT_VOICE = "tr-TR-EmelNeural"
RATE = "+15%"
PITCH = "-5Hz"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf"
FONT_DIR = Path("fonts")
FONT_PATH = FONT_DIR / "Montserrat-Bold.ttf"
MAX_CAPTION_WORDS = 2
MAX_CAPTION_DURATION = 0.62
FONT_SIZE = 56
STROKE_WIDTH = 4

NICHE_POOL = [
    "Komplo Teorileri ve Gizli Planlar",
    "Korkunc Gercekler",
    "Korkunc Tarihi Olaylar",
    "Cozulmemis Davalar",
    "Kaybolan Insanlarin Gizemli Hikayeleri",
    "Tuyler Urperten Suc Dosyalari",
    "Lanetli Yerler ve Korku Hikayeleri",
    "Aciklanamayan Paranormal Olaylar",
    "Karanlik Internet ve Teknoloji Sirlari",
    "Dunyanin En Rahatsiz Edici Gizemleri",
]

NICHE_PEXELS_QUERIES = {
    "Komplo Teorileri ve Gizli Planlar": ["secret files", "dark documents", "surveillance camera", "mysterious meeting", "classified papers"],
    "Korkunc Gercekler": ["dark forest", "abandoned hallway", "scary shadow", "eerie night", "creepy room"],
    "Korkunc Tarihi Olaylar": ["old abandoned building", "war ruins", "dark history", "old newspaper", "historic ruins night"],
    "Cozulmemis Davalar": ["detective board", "crime scene", "police investigation", "evidence board", "mystery documents"],
    "Kaybolan Insanlarin Gizemli Hikayeleri": ["missing person", "empty road night", "dark forest path", "abandoned car", "foggy road"],
    "Tuyler Urperten Suc Dosyalari": ["crime scene tape", "detective investigation", "dark alley", "police lights night", "evidence photos"],
    "Lanetli Yerler ve Korku Hikayeleri": ["haunted house", "abandoned mansion", "dark corridor", "creepy basement", "old cemetery fog"],
    "Aciklanamayan Paranormal Olaylar": ["paranormal activity", "ghostly shadow", "dark room", "foggy cemetery", "mysterious light"],
    "Karanlik Internet ve Teknoloji Sirlari": ["dark web", "hacker code", "cyber security dark", "server room dark", "phone screen night"],
    "Dunyanin En Rahatsiz Edici Gizemleri": ["mysterious place", "foggy forest", "abandoned place", "dark tunnel", "eerie landscape"],
}


def generate_script(niche: str) -> str:
    logger.info("Senaryo uretiliyor: %s", niche)
    prompt = f"""
Sen Turkce viral YouTube Shorts icin korku, gizem ve true-crime tarzi metinler yazan bir uzmansin.
Konu: {niche}
Asagidaki kurallara uygun, 30-40 saniyelik bir TURKCE metin yaz:
1. Ilk cumle tuyler urperten bir soru veya rahatsiz edici bir gercekle baslasin.
2. Komplo teorisi, korkunc gercek, cozulmemis dava, kayip olay veya karanlik gizem havasi tasisin.
3. Siddeti grafik anlatma; kanli detaylara girme. Merak, gerilim ve gizem kur.
4. Cumleler kisa, vurucu ve seslendirmeye uygun olsun.
5. Son cumle guclu ve dogal bir takip cagrisi icersin.
6. Emoji, sahne yonu, efekt, baslik ve madde isareti YOK. Sadece konusulacak metin.
Yalnizca metni dondur.
"""
    from g4f.client import Client

    client = Client()
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                timeout=60,
            )
            script = response.choices[0].message.content.strip().strip('"').strip("'")
            if len(script) < 30:
                logger.warning("Senaryo cok kisa, tekrar deneniyor.")
                time.sleep(2)
                continue
            logger.info("Senaryo hazir.")
            return script
        except Exception as exc:
            logger.warning("Senaryo deneme %s basarisiz: %s", attempt + 1, exc)
            time.sleep(3)
    raise RuntimeError("Senaryo uretilemedi.")


async def create_voiceover(script: str) -> Tuple[str, List[Tuple[float, float, str]]]:
    logger.info("Seslendirme olusturuluyor.")
    communicate = edge_tts.Communicate(script, DEFAULT_VOICE, rate=RATE, pitch=PITCH)
    word_timestamps = []

    with open(VOICEOVER_FILE, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timestamps.append((chunk["offset"] / 10_000_000, chunk["duration"] / 10_000_000, chunk["text"]))

    if not os.path.exists(VOICEOVER_FILE) or os.path.getsize(VOICEOVER_FILE) == 0:
        raise RuntimeError("Ses dosyasi olusturulamadi.")

    if not word_timestamps:
        logger.warning("Kelime zamanlamasi yok, ses suresine gore hizalama yapiliyor.")
        audio_clip = AudioFileClip(VOICEOVER_FILE)
        total_duration = max(float(audio_clip.duration), 1.0)
        audio_clip.close()
        words = [word for word in script.split() if word.strip()]
        if not words:
            raise RuntimeError("Senaryo bos, altyazi uretilemez.")
        total_chars = sum(max(len(word), 1) for word in words)
        current = 0.05
        usable_duration = max(total_duration - 0.10, 0.5)
        for word in words:
            duration = usable_duration * (max(len(word), 1) / total_chars)
            duration = max(duration, 0.16)
            word_timestamps.append((current, duration, word))
            current += duration

    logger.info("%s kelime zamanlandi.", len(word_timestamps))
    return VOICEOVER_FILE, word_timestamps


def extract_keywords(script: str, count: int = 5) -> list[str]:
    stop_words = {
        "icin", "gibi", "kadar", "ama", "fakat", "ancak", "degil", "evet", "hayir",
        "cok", "daha", "bir", "iki", "uc", "dort", "bes", "the", "and", "for", "with",
        "that", "this", "from", "are", "was", "were", "been", "being", "have", "has", "had",
    }
    words = re.findall(r"\b\w{4,}\b", script.lower())
    filtered = [word for word in words if word not in stop_words]
    filtered.sort(key=len, reverse=True)
    return filtered[:count]


def search_pexels_query(query: str) -> str | None:
    headers = {"Authorization": PEXELS_API_KEY}
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "per_page": 8, "orientation": "portrait", "size": "large"},
            timeout=20,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
        candidates = []
        for video in videos:
            for video_file in video.get("video_files", []):
                width = int(video_file.get("width") or 0)
                height = int(video_file.get("height") or 0)
                link = video_file.get("link")
                if not link or width <= 0 or height <= 0:
                    continue
                vertical_bonus = 10_000_000 if height >= width else 0
                quality_score = width * height + vertical_bonus
                candidates.append((quality_score, link))
        if candidates:
            candidates.sort(reverse=True)
            logger.info("Pexels arka plan secildi: %s", query)
            return candidates[0][1]
    except Exception as exc:
        logger.warning("Pexels aramasi basarisiz (%s): %s", query, exc)
    return None


def fetch_background_video(script: str, niche: str | None = None) -> str:
    queries = []
    if niche and niche in NICHE_PEXELS_QUERIES:
        queries.extend(NICHE_PEXELS_QUERIES[niche])

    keywords = extract_keywords(script)
    if keywords:
        queries.extend([" ".join(keywords[:2]), keywords[0]])
    queries.extend(["horror atmosphere", "dark mystery", "scary cinematic", "foggy abandoned place"])

    url = None
    for query in dict.fromkeys(queries):
        url = search_pexels_query(query)
        if url:
            break

    if not url:
        raise RuntimeError("Pexels'te uygun arka plan videosu bulunamadi.")

    with requests.get(url, stream=True, timeout=90) as response:
        response.raise_for_status()
        with open(BACKGROUND_FILE, "wb") as file:
            for chunk in response.iter_content(8192):
                if chunk:
                    file.write(chunk)

    if os.path.getsize(BACKGROUND_FILE) < 200_000:
        raise RuntimeError("Indirilen arka plan videosu bozuk veya cok kucuk.")
    return BACKGROUND_FILE


def ensure_font() -> str:
    if FONT_PATH.exists():
        return str(FONT_PATH.resolve())
    try:
        FONT_DIR.mkdir(exist_ok=True)
        with requests.get(FONT_URL, timeout=15) as response:
            response.raise_for_status()
            with open(FONT_PATH, "wb") as file:
                file.write(response.content)
        return str(FONT_PATH.resolve())
    except Exception:
        return "Arial-Bold"


def clean_caption_word(word: str) -> str:
    return re.sub(r"[^A-Za-z0-9'\-À-ÖØ-öø-ÿ]+", "", str(word)).strip()


def chunk_timestamps(word_ts):
    if not word_ts:
        return []

    chunks = []
    current_words = []
    chunk_start = word_ts[0][0]
    chunk_end = word_ts[0][0]

    for start, duration, word in word_ts:
        word = clean_caption_word(word)
        if not word:
            continue
        word_end = max(start + duration, start + 0.14)
        projected_duration = word_end - chunk_start

        if current_words and (len(current_words) >= MAX_CAPTION_WORDS or projected_duration > MAX_CAPTION_DURATION):
            chunks.append((chunk_start, max(chunk_end - chunk_start, 0.16), " ".join(current_words)))
            current_words = [word]
            chunk_start = start
            chunk_end = word_end
        else:
            current_words.append(word)
            chunk_end = word_end

    if current_words:
        chunks.append((chunk_start, max(chunk_end - chunk_start, 0.16), " ".join(current_words)))

    fixed = []
    for index, (start, duration, text) in enumerate(chunks):
        end = start + duration
        if index + 1 < len(chunks):
            next_start = chunks[index + 1][0]
            end = min(end, next_start - 0.015)
        fixed.append((start, max(end - start, 0.12), text))
    return fixed


def generate_captions(chunked_ts):
    if not chunked_ts:
        return []
    font = ensure_font()
    clips = []
    for start, duration, text in chunked_ts:
        text = re.sub(r"[^A-Za-z0-9'\-À-ÖØ-öø-ÿ ]+", "", str(text)).strip()
        if not text:
            continue
        clip = (
            TextClip(
                text,
                fontsize=FONT_SIZE,
                color="white",
                font=font,
                stroke_color="black",
                stroke_width=STROKE_WIDTH,
                method="caption" if len(text) > 12 else "label",
                size=(VIDEO_SIZE[0] - 180, None),
            )
            .set_start(start)
            .set_duration(duration)
            .set_position(("center", "center"))
        )
        clips.append(clip)
    return clips


def mix_background_music(audio_clip, music_path: str = "bg_music.mp3"):
    if not os.path.exists(music_path):
        return None
    try:
        background = AudioFileClip(music_path).fx(volumex, 0.06)
        background = audio_loop(background, duration=audio_clip.duration)
        return CompositeAudioClip([audio_clip, background])
    except Exception:
        return None


def assemble_video(bg_path: str, audio_path: str, chunked_ts, music_path: str | None = None) -> str:
    logger.info("Montaj basliyor.")
    bg_clip = VideoFileClip(bg_path)
    audio_clip = AudioFileClip(audio_path)
    target_duration = audio_clip.duration

    width, height = bg_clip.size
    if width / height < VIDEO_SIZE[0] / VIDEO_SIZE[1]:
        bg_clip = bg_clip.resize(width=VIDEO_SIZE[0])
        bg_clip = crop(bg_clip, y1=(bg_clip.h - VIDEO_SIZE[1]) // 2, y2=(bg_clip.h + VIDEO_SIZE[1]) // 2)
    else:
        bg_clip = bg_clip.resize(height=VIDEO_SIZE[1])
        bg_clip = crop(bg_clip, x1=(bg_clip.w - VIDEO_SIZE[0]) // 2, x2=(bg_clip.w + VIDEO_SIZE[0]) // 2)
    bg_clip = bg_clip.resize(VIDEO_SIZE)

    if bg_clip.duration < target_duration:
        bg_clip = bg_clip.loop(duration=target_duration)
    else:
        bg_clip = bg_clip.subclip(0, target_duration)

    final_audio = audio_clip
    if music_path:
        mixed = mix_background_music(audio_clip, music_path)
        if mixed:
            final_audio = mixed
    bg_clip = bg_clip.set_audio(final_audio)

    captions = generate_captions(chunked_ts)
    final = CompositeVideoClip([bg_clip] + captions, size=VIDEO_SIZE)
    final.write_videofile(
        OUTPUT_VIDEO,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="medium",
        threads=4,
        verbose=False,
        logger=None,
    )
    return OUTPUT_VIDEO


def get_youtube_service():
    client_secrets_json = os.getenv("CLIENT_SECRETS_JSON")
    if client_secrets_json:
        config = json.loads(client_secrets_json)
    elif Path(CLIENT_SECRETS_FILE).exists():
        with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
    else:
        raise RuntimeError("CLIENT_SECRETS_JSON bulunamadi.")

    client_config = config.get("installed") or config.get("web") or next(iter(config.values()))

    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_config["client_id"],
        client_secret=client_config["client_secret"],
        scopes=YOUTUBE_SCOPES,
    )
    credentials.refresh(Request())
    return build("youtube", "v3", credentials=credentials)


def upload_to_youtube(video_path: str, title: str, description: str, tags=None) -> str:
    if not os.path.exists(video_path):
        raise FileNotFoundError(video_path)
    if "#shorts" not in title.lower():
        title = f"{title} #shorts"

    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or ["shorts", "youtubeshorts", "viral", "korku", "gizem", "komplo teorileri", "cozulmemis dava"],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    logger.info("Yukleniyor: %s", title)
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("Yukleme: %s%%", int(status.progress() * 100))

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    logger.info("Yayinda: %s", url)
    return url


async def run_pipeline(niche: str):
    try:
        logger.info("Nis: %s", niche)
        script = generate_script(niche)
        logger.info("Senaryo:\n%s", script)
        audio, word_ts = await create_voiceover(script)
        chunked = chunk_timestamps(word_ts)
        background = fetch_background_video(script, niche)
        music = "bg_music.mp3" if os.path.exists("bg_music.mp3") else None
        final_path = assemble_video(background, audio, chunked, music)
        first_sentence = re.split(r"[.!?]", script)[0].strip()[:50]
        title = f"{niche}: {first_sentence}"
        description = (
            "Karanlik gercekler, komplo teorileri, cozulmemis davalar ve tuyler urperten gizemler.\n"
            "Yeni korku ve gizem Shorts videolari icin takipte kal.\n\n"
            "#shorts #korku #gizem #komplo #truecrime"
        )
        upload_to_youtube(final_path, title, description=description)
        logger.info("Tamamlandi.")
    except Exception as exc:
        logger.error("Hata: %s\n%s", exc, traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    selected_niche = random.choice(NICHE_POOL)
    asyncio.run(run_pipeline(selected_niche))
