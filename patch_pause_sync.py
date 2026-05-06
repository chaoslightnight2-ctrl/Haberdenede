from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def chunk_timestamps(word_ts):
    # Edge TTS WordBoundary gerçek kelime başlangıç/süre veriyor.
    # En yakın senkron için kelime zamanını ana kaynak yapıyoruz.
    # MP3 encoder / render farkı için küçük offset env ile ayarlanabilir.
    if not word_ts:
        return []

    try:
        sync_offset = float(os.getenv("SUBTITLE_SYNC_OFFSET_SECONDS", "-0.08"))
    except Exception:
        sync_offset = -0.08

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
            next_raw_start = cleaned[i + 1][0]
            next_display_start = cleaned[i + 1][2]
            # Kelime altyazısını bir sonraki kelime başlamadan bitir.
            display_end = min(raw_end + sync_offset + 0.07, next_display_start - 0.006)
            if display_end <= display_start:
                display_end = min(next_display_start - 0.006, display_start + 0.11)
        else:
            display_end = raw_end + sync_offset + 0.12

        duration = max(display_end - display_start, 0.10)
        chunks.append((display_start, duration, word))

    return chunks


def turkish_upper(text: str) -> str:
    table = str.maketrans({"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç"})
    return text.translate(table).upper()

'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('Tighter Edge TTS subtitle sync offset patch applied')
