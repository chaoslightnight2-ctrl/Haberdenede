from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

start = s.index('def chunk_timestamps(')
end = s.index('\ndef generate_captions(', start)

new_func = r'''def chunk_timestamps(word_ts):
    # Edge TTS WordBoundary gerçek kelime başlangıç/süre veriyor.
    # Bu yüzden ekstra tahmini boşluk ekleyip timestamp'i bozma.
    # Sadece 1-2 kelimelik caption grupları oluştur ve bitişi sonraki kelimeyi geçmeyecek şekilde ayarla.
    if not word_ts:
        return []

    cleaned = []
    for start, dur, word in word_ts:
        word_clean = clean_caption_word(word)
        if not word_clean:
            continue
        start = max(float(start), 0.0)
        dur = max(float(dur), 0.08)
        cleaned.append((start, dur, word_clean))
    if not cleaned:
        return []

    chunks = []
    i = 0
    while i < len(cleaned):
        start, dur, word = cleaned[i]
        words = [word]
        end = start + dur

        # En fazla 2 kelime göster. İkinci kelime sadece yakınsa aynı caption'a girsin.
        if i + 1 < len(cleaned):
            n_start, n_dur, n_word = cleaned[i + 1]
            gap = max(n_start - end, 0.0)
            combined_duration = (n_start + n_dur) - start
            if gap <= 0.22 and combined_duration <= MAX_CAPTION_DURATION and len(words) < MAX_CAPTION_WORDS:
                words.append(n_word)
                end = n_start + n_dur
                i += 1

        # Caption görünme süresi gerçek kelime süresinden çok kısa olmasın ama sonraki kelimeye taşmasın.
        if i + 1 < len(cleaned):
            next_start = cleaned[i + 1][0]
            natural_end = min(max(end + 0.10, start + 0.20), next_start - 0.01)
        else:
            natural_end = max(end + 0.12, start + 0.22)

        if natural_end <= start:
            natural_end = end
        chunks.append((start, max(natural_end - start, 0.12), ' '.join(words)))
        i += 1

    return chunks


def turkish_upper(text: str) -> str:
    table = str.maketrans({"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç"})
    return text.translate(table).upper()

'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('Edge TTS direct word-timing subtitle sync patch applied')
