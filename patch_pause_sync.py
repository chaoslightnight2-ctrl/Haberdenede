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
        dur = max(float(dur), 0.12)
        cleaned.append((start, dur, word_clean))
    if not cleaned: return []

    chunks = []
    cur_words = []
    chunk_start = cleaned[0][0]
    chunk_end = cleaned[0][0]

    for i, (start, dur, word) in enumerate(cleaned):
        word_end = start + dur
        next_start = cleaned[i + 1][0] if i + 1 < len(cleaned) else None
        next_gap = 0.0 if next_start is None else max(next_start - word_end, 0.0)
        projected_duration = word_end - chunk_start

        should_break = False
        if cur_words and len(cur_words) >= MAX_CAPTION_WORDS:
            should_break = True
        if cur_words and projected_duration > MAX_CAPTION_DURATION:
            should_break = True
        if cur_words and next_gap >= 0.32:
            should_break = True

        if should_break:
            chunks.append((chunk_start, chunk_end, ' '.join(cur_words)))
            cur_words = [word]
            chunk_start = start
            chunk_end = word_end
        else:
            cur_words.append(word)
            chunk_end = word_end

        # Küçük konuşma boşluklarında altyazıyı aniden söndürme.
        if next_start is not None:
            gap = max(next_start - chunk_end, 0.0)
            if 0.04 <= gap <= 0.28:
                chunk_end += gap * 0.55

    if cur_words:
        chunks.append((chunk_start, chunk_end, ' '.join(cur_words)))

    fixed = []
    for i, (start, end, text) in enumerate(chunks):
        if i + 1 < len(chunks):
            next_start = chunks[i + 1][0]
            gap = max(next_start - end, 0.0)
            if gap > 0.45:
                end = min(end + 0.10, next_start - 0.06)
            else:
                end = min(end + 0.04, next_start - 0.015)
        fixed.append((start, max(end - start, 0.14), text))
    return fixed

'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('Pause-aware subtitle sync patch applied')
