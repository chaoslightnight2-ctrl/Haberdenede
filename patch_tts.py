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
        for token in tokens:
            stripped = token.strip()
            if stripped.endswith((".", "!", "?")):
                pause_weights.append(0.34)
            elif stripped.endswith((",", ";", ":")):
                pause_weights.append(0.18)
            else:
                pause_weights.append(0.0)
        total_pause = min(sum(pause_weights), total_duration * 0.28)
        speech_duration = max(total_duration - total_pause - 0.10, 0.5)
        total_chars = sum(max(len(token.strip(".,!?;:")), 1) for token in tokens) or 1
        current = 0.05
        rows = []
        for token, pause in zip(tokens, pause_weights):
            clean_len = max(len(token.strip(".,!?;:")), 1)
            duration = max(speech_duration * (clean_len / total_chars), 0.16)
            rows.append((current, duration, token))
            current += duration + pause
        return rows

    logger.info("Ses oluşturuluyor. Sadece Edge TTS erkek ses kullanılacak. Voice=%s Rate=%s Pitch=%s", DEFAULT_VOICE, RATE, PITCH)
    word_timestamps: list[tuple[float, float, str]] = []
    try:
        if audio_path.exists():
            audio_path.unlink()
        communicate = edge_tts.Communicate(script, "tr-TR-AhmetNeural", rate=RATE, pitch=PITCH)
        with open(audio_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_timestamps.append((chunk["offset"] / 10_000_000, chunk["duration"] / 10_000_000, chunk["text"]))
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Edge TTS ses dosyası oluşturamadı")
        logger.info("Edge TTS erkek ses başarılı: tr-TR-AhmetNeural")
        return word_timestamps or estimate_with_pauses()
    except Exception as exc:
        if audio_path.exists():
            audio_path.unlink()
        raise RuntimeError(
            "Edge TTS erkek ses çalışmadı. Fallback kapalı; kadın veya robot ses kullanılmayacak. "
            f"Hata: {exc}"
        )

'''

p.write_text(s[:start] + replacement + s[end + 1 :], encoding="utf-8")
print("Edge-only male TTS patch applied")
