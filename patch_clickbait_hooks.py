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
        "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Sözcü", "Odatv", "Gerçek İzmir", "Konya Postası Gazetesi", "Anadolu Ajansı",
        "TRT Haber", "T24", "Gazete Duvar", "Cumhuriyet", "En Son Haber", "İHA", "DHA"
    ]
    for source in blocked_sources:
        summary = re.sub(re.escape(source), "", summary, flags=re.I)
    summary = re.sub(r"\s+", " ", summary).strip(" .-|:")
    return summary[:900]


def get_best_news_content_for_script(item: dict[str, Any]) -> str:
    article = clean_news_summary_for_script(item.get("article_text", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    title = clean_news_title_for_script(item.get("title", ""))
    if article and len(article.split()) >= 45:
        return article[:1300]
    if summary and len(summary.split()) >= 35 and normalize_text(summary) != normalize_text(title):
        return summary[:900]
    return ""


def is_generic_or_empty_script(script: str) -> bool:
    low = normalize_text(script)
    banned = [
        "google haber", "google news", "rss", "derlenen", "kapsamlı haber", "kapsamlı bilgiler",
        "haber içeriğine göre", "ayrıntılar sınırlı", "yeni açıklamalar", "resmi açıklamalar",
        "gelişmeler takip", "gelişmeleri aktarmaya devam", "konuya ilişkin detaylar", "detaylar netleşecek",
    ]
    if any(x in low for x in banned):
        return True
    meaningful_words = [w for w in low.split() if len(w) > 4]
    return len(meaningful_words) < 35


def fallback_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Gerçek haber içeriği yok, boş/genel metin üretilmeyecek: {title}")
    sentences = re.split(r"(?<=[.!?])\s+", content)
    body = " ".join(sentences[:4]).strip() or content
    return (
        f"Son dakika. {title}. "
        f"Bu gelişme gündemde dikkat çekebilir. "
        f"{body} "
        "Detaylar için takipte kal."
    )

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
Sen deneyimli bir Türkçe haber spikerisin. YouTube Shorts için düzgün, mantıklı ve profesyonel haber metni yaz.
Aşağıdaki GERÇEK HABER İÇERİĞİNDEN 35-45 saniyelik tek parça konuşma metni üret.

Zorunlu yapı:
1. Metin kesinlikle "Son dakika." diye başlasın.
2. İkinci cümle haberle ilgili clickbait ama mantıklı bir başlık cümlesi olsun.
3. Sonra haberin somut içeriğini anlat: kim, ne yaptı, nerede oldu, neden önemli, varsa sayı/karar/iddia ne?
4. Google News, Google Haberler, RSS, derlenen haber, kapsamlı haber gibi ifadeleri ASLA kullanma.
5. "Haberin içeriğine göre" ifadesini ASLA kullanma.
6. Site/kaynak adı okuma. Habertürk, Sabah, Yeni Şafak, NTV gibi medya isimlerini metne koyma.
7. Başlığı aynen tekrar edip durma; anlamı haber metnine çevir.
8. "Yeni açıklamalar bekleniyor", "detaylar netleşecek", "gelişmeleri takip edeceğiz" gibi boş cümleler kullanma.
9. Anlatım bozukluğu, tekrar, yarım cümle ve gereksiz abartı kullanma.
10. Verilen içerik dışında bilgi, tarih, kişi, sayı veya iddia uydurma.
11. Kaynakta kesin olmayan şeyi kesinmiş gibi söyleme.
12. Cümleler kısa, akıcı ve seslendirmeye uygun olsun.
13. Deprem, afet, kaza, ölüm ve adliye haberlerinde saygılı ve ölçülü kal.
14. Son cümle kısa ve doğal bir takip çağrısı olsun.

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
        script = response.choices[0].message.content.strip().strip('"').strip("'")
        script = re.sub(r"\s+", " ", script).strip()
        blocked = ["Google News", "Google Haberler", "RSS", "derlenen", "kapsamlı haber", "Haberin içeriğine göre", "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet", "Odatv", "Gerçek İzmir", "Konya Postası", "Anadolu Ajansı"]
        for source in blocked:
            script = re.sub(re.escape(source), "", script, flags=re.I)
        script = re.sub(r"\s+", " ", script).strip()
        if not script.lower().startswith("son dakika"):
            script = "Son dakika. " + script
        if len(script) < 220:
            raise RuntimeError("Metin çok kısa")
        if script.count(".") < 4:
            raise RuntimeError("Metin haber akışı için zayıf")
        if is_generic_or_empty_script(script):
            raise RuntimeError("AI genel/boş haber metni üretti")
        return script
    except Exception as exc:
        logger.warning("AI metni oluşmadı veya genel kaldı, içerikli fallback deneniyor: %s", exc)
        script = fallback_script(item)
        if is_generic_or_empty_script(script):
            raise RuntimeError("Fallback de genel kaldı, video metni iptal edildi")
        return script
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("No generic phrase script patch applied")
