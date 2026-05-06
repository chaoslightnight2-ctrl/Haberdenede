from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

s = s.replace('DEFAULT_VOICE = os.getenv("VOICE", "tr-TR-AhmetNeural")', 'DEFAULT_VOICE = os.getenv("VOICE", "tr-TR-AhmetNeural")')
s = s.replace('RATE = os.getenv("VOICE_RATE", "+8%")', 'RATE = os.getenv("VOICE_RATE", "+18%")')
s = s.replace('PITCH = os.getenv("VOICE_PITCH", "-3Hz")', 'PITCH = os.getenv("VOICE_PITCH", "-4Hz")')

start = s.index("async def create_voiceover(")
end = s.index("\ndef extract_keywords(", start)

replacement = '''async def create_voiceover(script: str, audio_path: Path) -> list[tuple[float, float, str]]:
    def estimate() -> list[tuple[float, float, str]]:
        audio_clip = AudioFileClip(str(audio_path))
        total_duration = max(float(audio_clip.duration), 1.0)
        audio_clip.close()
        words = [word for word in script.split() if word.strip()]
        total_chars = sum(max(len(word), 1) for word in words) or 1
        current = 0.05
        usable_duration = max(total_duration - 0.1, 0.5)
        rows = []
        for word in words:
            duration = max(usable_duration * (max(len(word), 1) / total_chars), 0.14)
            rows.append((current, duration, word))
            current += duration
        return rows

    logger.info("Ses oluşturuluyor. Öncelik: hızlı Türkçe erkek ses. Voice=%s Rate=%s Pitch=%s", DEFAULT_VOICE, RATE, PITCH)
    voices_to_try = []
    for voice in [DEFAULT_VOICE, "tr-TR-AhmetNeural"]:
        if voice not in voices_to_try:
            voices_to_try.append(voice)

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
                logger.info("Edge TTS başarılı: %s", voice)
                return word_timestamps or estimate()
        except Exception as exc:
            logger.warning("Edge TTS başarısız. Voice=%s Hata=%s", voice, exc)

    logger.warning("Erkek Edge sesi çalışmadı. Son çare olarak gTTS kullanılacak; bu ses erkek olmayabilir.")
    if audio_path.exists():
        audio_path.unlink()
    from gtts import gTTS
    gTTS(text=script, lang="tr", slow=False).save(str(audio_path))
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError("gTTS fallback ses oluşturamadı")
    return estimate()

'''

p.write_text(s[:start] + replacement + s[end + 1 :], encoding="utf-8")
print("Fast male voice patch applied")
