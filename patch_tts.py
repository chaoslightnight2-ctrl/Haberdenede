from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

s = s.replace('DEFAULT_VOICE = os.getenv("VOICE", "tr-TR-AhmetNeural")', 'DEFAULT_VOICE = os.getenv("VOICE", "tr-TR-AhmetNeural")')
s = s.replace('RATE = os.getenv("VOICE_RATE", "+8%")', 'RATE = os.getenv("VOICE_RATE", "+18%")')
s = s.replace('PITCH = os.getenv("VOICE_PITCH", "-3Hz")', 'PITCH = os.getenv("VOICE_PITCH", "-4Hz")')
s = s.replace('RATE = os.getenv("VOICE_RATE", "+15%")', 'RATE = os.getenv("VOICE_RATE", "+18%")')
s = s.replace('PITCH = os.getenv("VOICE_PITCH", "-5Hz")', 'PITCH = os.getenv("VOICE_PITCH", "-4Hz")')

start = s.index("async def create_voiceover(")
end = s.index("\ndef extract_keywords(", start)

replacement = '''async def create_voiceover(script: str, audio_path: Path) -> list[tuple[float, float, str]]:
    def estimate_with_pauses() -> list[tuple[float, float, str]]:
        audio_clip = AudioFileClip(str(audio_path))
        total_duration = max(float(audio_clip.duration), 1.0)
        audio_clip.close()

        tokens = [token for token in script.split() if token.strip()]
        if not tokens:
            raise RuntimeError("Senaryo boş, altyazı üretilemez")

        pause_weights = []
        clean_tokens = []
        for token in tokens:
            clean_tokens.append(token)
            stripped = token.strip()
            if stripped.endswith((".", "!", "?")):
                pause_weights.append(0.34)
            elif stripped.endswith((",", ";", ":")):
                pause_weights.append(0.18)
            else:
                pause_weights.append(0.0)

        total_pause = min(sum(pause_weights), total_duration * 0.28)
        speech_duration = max(total_duration - total_pause - 0.10, 0.5)
        total_chars = sum(max(len(token.strip(".,!?;:")), 1) for token in clean_tokens) or 1

        current = 0.05
        rows = []
        for token, pause in zip(clean_tokens, pause_weights):
            clean_len = max(len(token.strip(".,!?;:")), 1)
            duration = speech_duration * (clean_len / total_chars)
            duration = max(duration, 0.16)
            rows.append((current, duration, token))
            current += duration + pause
        return rows

    logger.info("Ses oluşturuluyor. Zorunlu erkek Edge sesi. Voice=%s Rate=%s Pitch=%s", DEFAULT_VOICE, RATE, PITCH)
    voices_to_try = []
    for voice in [DEFAULT_VOICE, "tr-TR-AhmetNeural"]:
        if voice not in voices_to_try:
            voices_to_try.append(voice)

    last_error = None
    for voice in voices_to_try:
        word_timestamps: list[tuple[float, float, str]] = []
        try:
            if audio_path.exists():
                audio_path.unlink()
            communicate = edge_tts.Communicate(script, voice, rate=RATE, pitch=PITCH)
            with open(audio_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        word_timestamps.append((chunk["offset"] / 10_000_000, chunk["duration"] / 10_000_000, chunk["text"]))
            if audio_path.exists() and audio_path.stat().st_size > 0:
                logger.info("Edge TTS erkek ses başarılı: %s", voice)
                return word_timestamps or estimate_with_pauses()
        except Exception as exc:
            last_error = exc
            logger.warning("Edge TTS erkek ses başarısız. Voice=%s Hata=%s", voice, exc)

    if audio_path.exists():
        audio_path.unlink()
    raise RuntimeError(
        "Erkek Edge TTS çalışmadı; kadın gTTS fallback özellikle kapatıldı. "
        "Edge TTS 403 verirse video üretilmez, çünkü kadın sese düşmesini istemiyorsun. "
        f"Son hata: {last_error}"
    )

'''

p.write_text(s[:start] + replacement + s[end + 1 :], encoding="utf-8")
print("Male-only Edge TTS patch applied with pause-aware timing")
