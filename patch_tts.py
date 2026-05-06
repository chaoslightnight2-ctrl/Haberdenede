from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")
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
            duration = max(usable_duration * (max(len(word), 1) / total_chars), 0.16)
            rows.append((current, duration, word))
            current += duration
        return rows

    logger.info("Ses oluşturuluyor. Voice=%s Rate=%s Pitch=%s", DEFAULT_VOICE, RATE, PITCH)
    word_timestamps: list[tuple[float, float, str]] = []
    try:
        communicate = edge_tts.Communicate(script, DEFAULT_VOICE, rate=RATE, pitch=PITCH)
        with open(audio_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_timestamps.append((chunk["offset"] / 10_000_000, chunk["duration"] / 10_000_000, chunk["text"]))
        if audio_path.exists() and audio_path.stat().st_size > 0:
            return word_timestamps or estimate()
        raise RuntimeError("Edge TTS boş ses döndürdü")
    except Exception as exc:
        logger.warning("Edge TTS başarısız, gTTS fallback deneniyor: %s", exc)
        if audio_path.exists():
            audio_path.unlink()
        from gtts import gTTS
        gTTS(text=script, lang="tr", slow=False).save(str(audio_path))
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("gTTS fallback ses oluşturamadı")
        return estimate()

'''

p.write_text(s[:start] + replacement + s[end + 1 :], encoding="utf-8")
print("TTS fallback patch applied")
