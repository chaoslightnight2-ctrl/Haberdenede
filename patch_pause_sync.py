from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

# Ses dalga formundan konuşma başlangıcı/bitişi ölçmek için numpy gerekir.
if "import numpy as np" not in s:
    s = s.replace("import traceback\n", "import traceback\nimport numpy as np\n")

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def detect_speech_bounds_from_audio(audio_path: Path) -> tuple[float | None, float | None, float | None]:
    # Final MP3 dosyasının gerçek dalga formundan konuşma başlangıç/bitişini bul.
    # Bu, Edge timestamp ile MP3 encoder başlangıç boşluğu arasındaki kaymayı düzeltir.
    try:
        audio_clip = AudioFileClip(str(audio_path))
        duration = float(audio_clip.duration)
        fps = 16000
        arr = audio_clip.to_soundarray(fps=fps)
        audio_clip.close()
        if arr is None or len(arr) == 0:
            return None, None, duration
        if getattr(arr, "ndim", 1) > 1:
            mono = np.mean(np.abs(arr), axis=1)
        else:
            mono = np.abs(arr)
        if mono.size == 0:
            return None, None, duration

        frame = max(int(0.02 * fps), 1)
        usable = mono[: (mono.size // frame) * frame]
        if usable.size == 0:
            return None, None, duration
        env = usable.reshape(-1, frame).mean(axis=1)
        max_amp = float(env.max()) if env.size else 0.0
        if max_amp <= 0:
            return None, None, duration
        threshold = max(max_amp * 0.035, float(np.percentile(env, 70)) * 1.8, 0.002)
        active = np.where(env > threshold)[0]
        if active.size == 0:
            threshold = max(max_amp * 0.02, 0.001)
            active = np.where(env > threshold)[0]
        if active.size == 0:
            return None, None, duration
        speech_start = max((int(active[0]) * frame / fps) - 0.02, 0.0)
        speech_end = min(((int(active[-1]) + 1) * frame / fps) + 0.04, duration)
        logger.info("Ses dalga formu konuşma sınırı: start=%.3f end=%.3f duration=%.3f", speech_start, speech_end, duration)
        return speech_start, speech_end, duration
    except Exception as exc:
        logger.warning("Ses dalga formu analizi yapılamadı: %s", exc)
        return None, None, None


def normalize_word_timestamps_to_audio(word_ts, audio_path: Path):
    # Edge TTS WordBoundary zamanlarını final ses dosyasındaki gerçek konuşma aralığına kalibre et.
    # Böylece altyazı sadece teorik TTS zamanına değil, gerçekten duyulan sese oturur.
    if not word_ts:
        return word_ts
    try:
        speech_start, speech_end, audio_duration = detect_speech_bounds_from_audio(audio_path)
        first_start = min(float(start) for start, _, _ in word_ts)
        last_end = max(float(start) + max(float(dur), 0.0) for start, dur, _ in word_ts)
        if speech_start is not None and speech_end is not None and last_end > first_start:
            source_span = last_end - first_start
            target_span = max(speech_end - speech_start, 0.1)
            scale = target_span / source_span
            if 0.85 <= scale <= 1.15:
                logger.info("Altyazı gerçek ses dalgasına kalibre edildi: shift=%.3f scale=%.4f", speech_start - first_start, scale)
                return [
                    (speech_start + (float(start) - first_start) * scale, max(float(dur) * scale, 0.04), word)
                    for start, dur, word in word_ts
                ]
            logger.warning("Dalga formu scale olağandışı, süre normalizasyonuna düşülüyor: scale=%.4f", scale)

        if audio_duration:
            last_end = max(float(start) + max(float(dur), 0.0) for start, dur, _ in word_ts)
            scale = float(audio_duration) / last_end if last_end > 0 else 1.0
            if 0.92 <= scale <= 1.08:
                logger.info("Altyazı zamanları ses süresine göre normalize edildi: scale=%.4f", scale)
                return [(float(start) * scale, float(dur) * scale, word) for start, dur, word in word_ts]
    except Exception as exc:
        logger.warning("Altyazı zaman normalizasyonu yapılamadı: %s", exc)
    return word_ts


def chunk_timestamps(word_ts):
    # Kalibrasyon sonrası kelime zamanlarını neredeyse birebir kullan.
    # Offset varsayılan 0: artık tahmini öne/arkaya alma yok.
    if not word_ts:
        return []

    try:
        sync_offset = float(os.getenv("SUBTITLE_SYNC_OFFSET_SECONDS", "0"))
    except Exception:
        sync_offset = 0.0

    cleaned = []
    for start, dur, word in word_ts:
        word_clean = clean_caption_word(word)
        if not word_clean:
            continue
        raw_start = max(float(start), 0.0)
        raw_dur = max(float(dur), 0.05)
        display_start = max(raw_start + sync_offset, 0.0)
        cleaned.append((raw_start, raw_dur, display_start, word_clean))
    if not cleaned:
        return []

    chunks = []
    for i, (raw_start, raw_dur, display_start, word) in enumerate(cleaned):
        raw_end = raw_start + raw_dur
        if i + 1 < len(cleaned):
            next_display_start = cleaned[i + 1][2]
            display_end = min(raw_end + sync_offset + 0.035, next_display_start - 0.004)
            if display_end <= display_start:
                display_end = min(next_display_start - 0.004, display_start + 0.08)
        else:
            display_end = raw_end + sync_offset + 0.08

        duration = max(display_end - display_start, 0.07)
        chunks.append((display_start, duration, word))

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
print('Subtitle timestamps calibrated to actual audio waveform')
