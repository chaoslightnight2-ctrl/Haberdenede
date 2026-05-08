from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

# Ses dalga formundan konuşma başlangıcını ölçmek için numpy gerekir.
if "import numpy as np" not in s:
    s = s.replace("import traceback\n", "import traceback\nimport numpy as np\n")

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def detect_speech_bounds_from_audio(audio_path: Path) -> tuple[float | None, float | None, float | None]:
    try:
        audio_clip = AudioFileClip(str(audio_path))
        duration = float(audio_clip.duration)
        fps = 16000
        arr = audio_clip.to_soundarray(fps=fps)
        audio_clip.close()
        if arr is None or len(arr) == 0:
            return None, None, duration
        mono = np.mean(np.abs(arr), axis=1) if getattr(arr, "ndim", 1) > 1 else np.abs(arr)
        if mono.size == 0:
            return None, None, duration
        frame = max(int(0.015 * fps), 1)
        usable = mono[: (mono.size // frame) * frame]
        if usable.size == 0:
            return None, None, duration
        env = usable.reshape(-1, frame).mean(axis=1)
        max_amp = float(env.max()) if env.size else 0.0
        if max_amp <= 0:
            return None, None, duration
        noise = float(np.percentile(env, 35))
        threshold = max(max_amp * 0.025, noise * 3.0, 0.0015)
        active = np.where(env > threshold)[0]
        if active.size == 0:
            threshold = max(max_amp * 0.015, 0.001)
            active = np.where(env > threshold)[0]
        if active.size == 0:
            return None, None, duration
        speech_start = max((int(active[0]) * frame / fps) - 0.015, 0.0)
        speech_end = min(((int(active[-1]) + 1) * frame / fps) + 0.04, duration)
        logger.info("Ses dalga formu konuşma sınırı: start=%.3f end=%.3f duration=%.3f", speech_start, speech_end, duration)
        return speech_start, speech_end, duration
    except Exception as exc:
        logger.warning("Ses dalga formu analizi yapılamadı: %s", exc)
        return None, None, None


def normalize_word_timestamps_to_audio(word_ts, audio_path: Path):
    if not word_ts:
        return word_ts
    try:
        speech_start, speech_end, audio_duration = detect_speech_bounds_from_audio(audio_path)
        first_start = min(float(start) for start, _, _ in word_ts)
        last_end = max(float(start) + max(float(dur), 0.0) for start, dur, _ in word_ts)
        shift = 0.0
        if speech_start is not None:
            shift = speech_start - first_start
        scale = 1.0
        if speech_start is not None and speech_end is not None and last_end > first_start:
            source_span = last_end - first_start
            target_span = speech_end - speech_start
            candidate_scale = target_span / source_span if source_span > 0 else 1.0
            if 0.985 <= candidate_scale <= 1.015:
                scale = candidate_scale
        logger.info("Altyazı sesle hizalandı: shift=%.3f scale=%.5f", shift, scale)
        return [
            (max((float(start) - first_start) * scale + first_start + shift, 0.0), max(float(dur) * scale, 0.04), word)
            for start, dur, word in word_ts
        ]
    except Exception as exc:
        logger.warning("Altyazı zaman normalizasyonu yapılamadı: %s", exc)
    return word_ts


def chunk_timestamps(word_ts):
    # Kelime başlangıcı gerçek TTS zamanıdır.
    # Kısa boşluklarda caption biraz kalsın; uzun durakta mutlaka kesilsin.
    if not word_ts:
        return []

    try:
        sync_offset = float(os.getenv("SUBTITLE_SYNC_OFFSET_SECONDS", "0"))
    except Exception:
        sync_offset = 0.0
    try:
        pause_cutoff = float(os.getenv("SUBTITLE_PAUSE_CUTOFF_SECONDS", "0.18"))
    except Exception:
        pause_cutoff = 0.18
    try:
        max_hold = float(os.getenv("SUBTITLE_MAX_HOLD_AFTER_WORD_SECONDS", "0.10"))
    except Exception:
        max_hold = 0.10

    cleaned = []
    for start, dur, word in word_ts:
        word_clean = clean_caption_word(word)
        if not word_clean:
            continue
        cleaned.append((max(float(start) + sync_offset, 0.0), max(float(dur), 0.04), word_clean))
    if not cleaned:
        return []

    chunks = []
    for i, (start, dur, word) in enumerate(cleaned):
        word_end = start + dur
        if i + 1 < len(cleaned):
            next_start = cleaned[i + 1][0]
            gap = max(next_start - word_end, 0.0)
            if gap > pause_cutoff:
                # Ses duruyorsa altyazı da dursun.
                end = word_end + min(max_hold, gap * 0.25)
            else:
                # Küçük doğal boşluklarda bir sonraki kelimeye kadar kalabilir.
                end = next_start - 0.004
            end = max(end, start + 0.06)
            end = min(end, next_start - 0.004) if next_start > start else end
        else:
            end = word_end + max_hold
        chunks.append((start, max(end - start, 0.06), word))
    return chunks


def turkish_upper(text: str) -> str:
    table = str.maketrans({"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç"})
    return text.translate(table).upper()

'''

s = s[:start] + new_func + s[end:]

old = "captions = generate_captions(chunk_timestamps(word_ts))"
new = "word_ts = normalize_word_timestamps_to_audio(word_ts, audio_path)\n    captions = generate_captions(chunk_timestamps(word_ts))"
s = s.replace(old, new)

p.write_text(s, encoding='utf-8')
print('Subtitle pauses now stop during longer voice gaps')
