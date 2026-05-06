from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# Sabit altyazı parametreleri: tüm caption'lar aynı boyutta ve aynı stilde görünsün.
s = s.replace("MAX_CAPTION_WORDS = 3", "MAX_CAPTION_WORDS = 2")
s = s.replace("MAX_CAPTION_DURATION = 0.75", "MAX_CAPTION_DURATION = 0.62")
s = s.replace("FONT_SIZE = 58", "FONT_SIZE = 56")
s = s.replace("STROKE_WIDTH = 4", "STROKE_WIDTH = 4")
s = s.replace("max(usable_duration * (max(len(word), 1) / total_chars), 0.14)", "max(usable_duration * (max(len(word), 1) / total_chars), 0.16)")

clean_start = s.index("def clean_caption_word(")
chunk_start = s.index("\ndef chunk_timestamps(", clean_start)
generate_start = s.index("\ndef generate_captions(", chunk_start)
mix_start = s.index("\ndef mix_background_music(", generate_start)

clean_func = r'''def clean_caption_word(word: str) -> str:
    # Türkçe karakterleri koru, sadece gereksiz noktalama/emoji temizle.
    return re.sub(r"[^A-Za-z0-9'\-À-ÖØ-öø-ÿçğıöşüÇĞİÖŞÜ]+", "", str(word)).strip()

'''

chunk_func = r'''def chunk_timestamps(word_ts):
    if not word_ts: return []
    chunks = []
    cur_words, chunk_start, chunk_end = [], word_ts[0][0], word_ts[0][0]
    for start, dur, word in word_ts:
        word = clean_caption_word(word)
        if not word:
            continue
        word_end = max(start + dur, start + 0.14)
        projected_duration = word_end - chunk_start
        if cur_words and (len(cur_words) >= MAX_CAPTION_WORDS or projected_duration > MAX_CAPTION_DURATION):
            chunks.append((chunk_start, max(chunk_end - chunk_start, 0.16), " ".join(cur_words)))
            cur_words, chunk_start, chunk_end = [word], start, word_end
        else:
            cur_words.append(word)
            chunk_end = word_end
    if cur_words:
        chunks.append((chunk_start, max(chunk_end - chunk_start, 0.16), " ".join(cur_words)))
    fixed = []
    for i, (start, dur, text) in enumerate(chunks):
        end = start + dur
        if i + 1 < len(chunks):
            next_start = chunks[i + 1][0]
            end = min(end, next_start - 0.015)
        fixed.append((start, max(end - start, 0.12), text))
    return fixed

'''

generate_func = r'''def generate_captions(chunked_ts):
    if not chunked_ts: return []
    font = ensure_font()
    clips = []
    caption_box = (VIDEO_SIZE[0] - 180, 170)
    for start, dur, text in chunked_ts:
        text = re.sub(r"[^A-Za-z0-9'\-À-ÖØ-öø-ÿçğıöşüÇĞİÖŞÜ ]+", "", str(text)).strip()
        if not text:
            continue
        # Hep aynı TextClip modu, aynı kutu, aynı font ve aynı pozisyon.
        # Böylece bazı altyazılar büyük bazıları küçük görünmez.
        txt = (TextClip(text.upper(), fontsize=FONT_SIZE, color="white", font=font,
                       stroke_color="black", stroke_width=STROKE_WIDTH,
                       method="caption", size=caption_box, align="center")
               .set_start(start).set_duration(dur).set_position(("center", "center")))
        clips.append(txt)
    return clips

'''

s = s[:clean_start] + clean_func + chunk_func + generate_func + s[mix_start + 1:]
p.write_text(s, encoding="utf-8")
print("Consistent subtitle size/style patch applied")
