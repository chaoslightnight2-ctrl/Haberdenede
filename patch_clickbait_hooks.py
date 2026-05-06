from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

fallback_start = s.index("def fallback_script(")
fallback_end = s.index("\ndef generate_news_script(", fallback_start)
new_fallback = r'''def clean_news_title_for_script(title: str) -> str:
    title = strip_html(title or "")
    title = re.sub(r"\s*\|\s*.*$", "", title).strip()
    title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
    title = re.sub(r"(?i)son dakika[:\s-]*", "", title).strip()
    title = re.sub(r"(?i)video videosunu izle", "", title).strip()
    title = re.sub(r"(?i)son dakika haberleri", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip(" .-|:")
    return title[:145]


def clean_news_summary_for_script(summary: str) -> str:
    summary = strip_html(summary or "")
    summary = re.sub(r"\s*\|\s*.*$", "", summary).strip()
    summary = re.sub(r"\s*-\s*[^-]+$", "", summary).strip()
    summary = re.sub(r"(?i)son dakika haberleri", "", summary).strip()
    summary = re.sub(r"(?i)video videosunu izle", "", summary).strip()
    blocked_sources = [
        "Google News", "Google Haberler", "Google haberlerden", "RSS", "derlenen", "kapsamlı haber",
        "Haberin içeriğine göre", "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Sözcü", "Odatv", "Gerçek İzmir", "Konya Postası Gazetesi", "Anadolu Ajansı",
        "TRT Haber", "T24", "Gazete Duvar", "Cumhuriyet", "En Son Haber", "İHA", "DHA"
    ]
    for source in blocked_sources:
        summary = re.sub(re.escape(source), "", summary, flags=re.I)
    summary = re.sub(r"\s+", " ", summary).strip(" .-|:")
    return summary[:1200]


def get_best_news_content_for_script(item: dict[str, Any]) -> str:
    article = clean_news_summary_for_script(item.get("article_text", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    title = clean_news_title_for_script(item.get("title", ""))
    if article and len(article.split()) >= 45:
        return article[:1400]
    if summary and len(summary.split()) >= 35 and normalize_text(summary) != normalize_text(title):
        return summary[:900]
    return ""


def make_clickbait_hook(title: str) -> str:
    title = clean_news_title_for_script(title)
    title = re.sub(r"[.!?]+$", "", title).strip()
    if not title:
        return "Bu olayın arkasındaki detaylar dikkat çekiyor."
    return f"Bu olayın arkasındaki detaylar dikkat çekiyor: {title}."


def split_clean_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text or "")
    result = []
    for sentence in raw:
        sentence = re.sub(r"\s+", " ", sentence).strip(" .")
        if len(sentence) < 18:
            continue
        low = normalize_text(sentence)
        banned = [
            "google haber", "google news", "rss", "derlenen", "kapsamlı haber", "haber içeriğine göre",
            "yeni açıklamalar", "detaylar netleşecek", "gelişmeleri takip", "gelişmeleri aktarmaya devam",
            "konuya ilişkin", "ayrıntılar sınırlı", "resmi açıklamalar"
        ]
        if any(x in low for x in banned):
            continue
        result.append(sentence + ".")
    return result


def dedupe_sentences(sentences: list[str], limit: int = 5) -> list[str]:
    chosen = []
    seen_keys = set()
    for sentence in sentences:
        key_words = [w for w in normalize_text(sentence).split() if len(w) > 3]
        key = " ".join(key_words[:10])
        if not key or key in seen_keys:
            continue
        if any(similarity(sentence, old) >= 0.70 for old in chosen):
            continue
        seen_keys.add(key)
        chosen.append(sentence)
        if len(chosen) >= limit:
            break
    return chosen


def build_body_from_content(content: str, title: str) -> str:
    sentences = dedupe_sentences(split_clean_sentences(content), limit=5)
    title_norm = normalize_text(title)
    filtered = []
    for sentence in sentences:
        if title_norm and similarity(sentence, title) >= 0.82:
            continue
        filtered.append(sentence)
    if len(filtered) < 2:
        filtered = sentences
    body = " ".join(filtered[:4]).strip()
    if len(body.split()) < 28:
        raise RuntimeError("Haber gövdesi tekrarsız ve yeterli değil")
    return body


def is_generic_or_empty_script(script: str) -> bool:
    low = normalize_text(script)
    banned = [
        "google haber", "google news", "rss", "derlenen", "kapsamlı haber", "kapsamlı bilgiler",
        "haber içeriğine göre", "ayrıntılar sınırlı", "yeni açıklamalar", "resmi açıklamalar",
        "gelişmeler takip", "gelişmeleri aktarmaya devam", "konuya ilişkin detaylar", "detaylar netleşecek",
    ]
    if any(x in low for x in banned):
        return True
    sentences = split_clean_sentences(script)
    if len(sentences) >= 2:
        for i, sentence in enumerate(sentences):
            for other in sentences[i+1:]:
                if similarity(sentence, other) >= 0.78:
                    return True
    meaningful_words = [w for w in low.split() if len(w) > 4]
    return len(meaningful_words) < 35


def cleanup_generated_script(script: str, title: str) -> str:
    blocked = [
        "Google News", "Google Haberler", "RSS", "derlenen", "kapsamlı haber", "Haberin içeriğine göre",
        "Son dakika", "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Odatv", "Gerçek İzmir", "Konya Postası", "Anadolu Ajansı"
    ]
    for source in blocked:
        script = re.sub(re.escape(source), "", script, flags=re.I)
    script = re.sub(r"\s+", " ", script).strip(" .")
    sentences = dedupe_sentences(split_clean_sentences(script), limit=6)
    if len(sentences) < 3:
        raise RuntimeError("AI metni yeterli sayıda farklı cümle üretmedi")
    final = " ".join(sentences[:5]).strip()
    if not final.endswith("."):
        final += "."
    return final


def fallback_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Gerçek haber içeriği yok, boş/genel metin üretilmeyecek: {title}")
    hook = make_clickbait_hook(title)
    body = build_body_from_content(content, title)
    return f"{hook} {body} Daha fazlası için takipte kal."

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Haber içeriği yetersiz, video metni üretilmeyecek: {title}")

    prompt = f"""
Sen deneyimli bir Türkçe haber spikerisin. YouTube Shorts için tek parça, düzgün ve akıcı konuşma metni yaz.

Metin yapısı kesinlikle şu sırada olacak:
[İlgi çekici clickbait başlık]
[Haber içeriği detaylı ama kısa]
[Takip mesajı]

Kurallar:
- Aynı cümleyi veya aynı anlamı tekrar etme.
- Her cümle yeni bir bilgi taşısın.
- Köşeli parantezleri yazma, başlık yazma, maddeleme yapma.
- İlk cümle haberle ilgili merak uyandıran clickbait başlık cümlesi olsun.
- İkinci bölümde gerçek haber içeriğini kısa ama detaylı anlat: kim, ne yaptı, nerede oldu, varsa sayı/karar/iddia ne?
- Son cümle doğal takip mesajı olsun.
- Google News, RSS, derlenen haber, kapsamlı haber, haberin içeriğine göre gibi ifadeleri ASLA kullanma.
- Site/kaynak adı okuma.
- Yeni açıklamalar bekleniyor, detaylar netleşecek, gelişmeleri takip edeceğiz gibi boş cümleler kullanma.
- Verilen içerik dışında bilgi, tarih, kişi, sayı veya iddia uydurma.
- Kaynakta kesin olmayan şeyi kesinmiş gibi söyleme.
- Cümleler kısa, akıcı ve seslendirmeye uygun olsun.
- Deprem, afet, kaza, ölüm ve adliye haberlerinde saygılı ve ölçülü kal.
- 35-45 saniyelik tek parça konuşma metni üret.

Haber başlığı: {title}
Gerçek haber içeriği: {content}
"""
    try:
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            timeout=90,
        )
        script = cleanup_generated_script(response.choices[0].message.content.strip().strip('"').strip("'"), title)
        if len(script) < 200:
            raise RuntimeError("Metin çok kısa")
        if script.count(".") < 3:
            raise RuntimeError("Metin haber akışı için zayıf")
        if is_generic_or_empty_script(script):
            raise RuntimeError("AI genel/tekrarlı haber metni üretti")
        return script
    except Exception as exc:
        logger.warning("AI metni oluşmadı veya tekrarlı kaldı, tekrarsız fallback kullanılıyor: %s", exc)
        script = fallback_script(item)
        if is_generic_or_empty_script(script):
            raise RuntimeError("Fallback de genel veya tekrarlı kaldı, video metni iptal edildi")
        return script
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("No-repeat script patch applied")
