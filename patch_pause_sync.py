from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def chunk_timestamps(word_ts):
    if not word_ts: return []
    cleaned = []
    for start, dur, word in word_ts:
        word_clean = clean_caption_word(word)
        if not word_clean:
            continue
        start = max(float(start), 0.0)
        dur = max(float(dur), 0.10)
        cleaned.append((start, dur, word_clean))
    if not cleaned: return []

    chunks = []
    cur_words = []
    chunk_start = cleaned[0][0]
    chunk_end = cleaned[0][0]

    for i, (start, dur, word) in enumerate(cleaned):
        word_end = start + dur
        next_start = cleaned[i + 1][0] if i + 1 < len(cleaned) else None
        projected_duration = word_end - chunk_start

        should_break_before_word = False
        if cur_words and len(cur_words) >= MAX_CAPTION_WORDS:
            should_break_before_word = True
        if cur_words and projected_duration > MAX_CAPTION_DURATION:
            should_break_before_word = True

        if should_break_before_word:
            chunks.append((chunk_start, chunk_end, ' '.join(cur_words)))
            cur_words = [word]
            chunk_start = start
            chunk_end = word_end
        else:
            cur_words.append(word)
            chunk_end = max(chunk_end, word_end)

        # Edge TTS WordBoundary kelime başlangıçlarını veriyor; aradaki fark gerçek ses boşluğu.
        # Küçük/orta boşluklarda mevcut altyazıyı açık tut, uzun durakta temiz kes.
        if next_start is not None:
            gap = max(next_start - chunk_end, 0.0)
            if 0.03 <= gap <= 0.65:
                chunk_end += gap * 0.82
            elif gap > 0.65:
                chunk_end += min(0.18, gap * 0.25)
                chunks.append((chunk_start, chunk_end, ' '.join(cur_words)))
                cur_words = []
                chunk_start = next_start
                chunk_end = next_start

    if cur_words:
        chunks.append((chunk_start, chunk_end, ' '.join(cur_words)))

    fixed = []
    for i, (start, end, text) in enumerate(chunks):
        if not text.strip():
            continue
        if i + 1 < len(chunks):
            next_start = chunks[i + 1][0]
            gap = max(next_start - end, 0.0)
            if gap <= 0.30:
                end = min(next_start - 0.01, end + gap * 0.80)
            elif gap <= 0.80:
                end = min(next_start - 0.04, end + 0.16)
            else:
                end = min(next_start - 0.07, end + 0.20)
        fixed.append((start, max(end - start, 0.16), text))
    return fixed


def turkish_upper(text: str) -> str:
    table = str.maketrans({"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç"})
    return text.translate(table).upper()

'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('Improved voice-pause subtitle sync patch applied without deleting turkish_upper')
