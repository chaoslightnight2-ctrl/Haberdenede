from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def normalize_word_timestamps_to_audio(word_ts, audio_path: Path):
    # Edge TTS WordBoundary zamanları bazen final MP3/AAC süresiyle küçük fark gösterebilir.
    # Bu fonksiyon kelime zamanlarını final ses dosyasının gerçek süresine göre ölçekler.
    if not word_ts:
        return word_ts
    try:
        audio_clip = AudioFileClip(str(audio_path))
        audio_duration = float(audio_clip.duration)
        audio_clip.close()
        last_end = max(float(start) + max(float(dur), 0.0) for start, dur, _ in word_ts)
        if last_end > 0 and audio_duration > 0:
            scale = audio_duration / last_end
            if 0.92 <= scale <= 1.08:
                logger.info("Altyazı zamanları ses süresine göre normalize edildi: scale=%.4f", scale)
                return [(float(start) * scale, float(dur) * scale, word) for start, dur, word in word_ts]
            logger.warning("Altyazı scale olağandışı, normalize edilmedi: scale=%.4f audio=%.3f last=%.3f", scale, audio_duration, last_end)
    except Exception as exc:
        logger.warning("Altyazı zaman normalizasyonu yapılamadı: %s", exc)
    return word_ts


def chunk_timestamps(word_ts):
    # Edge TTS WordBoundary gerçek kelime başlangıç/süre veriyor.
    # En yakın senkron için kelime zamanını ana kaynak yapıyoruz.
    # MP3 encoder / render farkı için küçük offset env ile ayarlanabilir.
    if not word_ts:
        return []

    try:
        sync_offset = float(os.getenv("SUBTITLE_SYNC_OFFSET_SECONDS", "-0.04"))
    except Exception:
        sync_offset = -0.04

    cleaned = []
    for start, dur, word in word_ts:
        word_clean = clean_caption_word(word)
        if not word_clean:
            continue
        raw_start = max(float(start), 0.0)
        raw_dur = max(float(dur), 0.06)
        display_start = max(raw_start + sync_offset, 0.0)
        cleaned.append((raw_start, raw_dur, display_start, word_clean))
    if not cleaned:
        return []

    chunks = []
    for i, (raw_start, raw_dur, display_start, word) in enumerate(cleaned):
        raw_end = raw_start + raw_dur
        if i + 1 < len(cleaned):
            next_display_start = cleaned[i + 1][2]
            display_end = min(raw_end + sync_offset + 0.06, next_display_start - 0.006)
            if display_end <= display_start:
                display_end = min(next_display_start - 0.006, display_start + 0.10)
        else:
            display_end = raw_end + sync_offset + 0.10

        duration = max(display_end - display_start, 0.09)
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
print('Subtitle word timestamps normalized to final audio duration')
