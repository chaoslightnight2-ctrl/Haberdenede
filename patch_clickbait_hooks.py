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
        "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Sözcü", "Odatv", "Gerçek İzmir", "Konya Postası Gazetesi", "Anadolu Ajansı",
        "TRT Haber", "T24", "Gazete Duvar", "Cumhuriyet"
    ]
    for source in blocked_sources:
        summary = summary.replace(source, "")
    summary = re.sub(r"\s+", " ", summary).strip(" .-|:")
    return summary[:380]


def fallback_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    if summary and normalize_text(summary) != normalize_text(title):
        detail = f"Haberde öne çıkan bilgiye göre {summary}."
    else:
        detail = "Ayrıntılar geldikçe olayın etkisi daha net anlaşılacak."
    return (
        f"Son dakika. {title}. "
        f"Bu gelişme gündemde geniş yankı uyandırabilir. "
        f"{detail} "
        "Şimdi gözler konuyla ilgili yapılacak yeni açıklamalarda. Gelişmeleri aktarmaya devam edeceğiz. Takipte kal."
    )

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    prompt = f"""
Sen deneyimli bir Türkçe haber spikerisin. YouTube Shorts için düzgün, mantıklı ve profesyonel haber metni yaz.
Aşağıdaki haberden 35-45 saniyelik tek parça konuşma metni üret.

Zorunlu yapı:
1. Metin kesinlikle "Son dakika." diye başlasın.
2. İkinci cümle haberle ilgili clickbait ama mantıklı bir başlık cümlesi olsun.
3. Sonra haberi açık, düzgün ve anlaşılır Türkçeyle anlat.
4. Site/kaynak adı okuma. Habertürk, Sabah, Yeni Şafak, NTV gibi medya isimlerini metne koyma.
5. Başlığı aynen tekrar edip durma; anlamı haber metnine çevir.
6. Anlatım bozukluğu, tekrar, yarım cümle ve gereksiz abartı kullanma.
7. Verilen başlık ve özet dışında bilgi, tarih, kişi, sayı veya iddia uydurma.
8. Kaynakta kesin olmayan şeyi kesinmiş gibi söyleme.
9. Olayın neden önemli olabileceğini mantık çerçevesinde açıkla.
10. Cümleler kısa, akıcı ve seslendirmeye uygun olsun.
11. Deprem, afet, kaza, ölüm ve adliye haberlerinde saygılı ve ölçülü kal.
12. Emoji, madde işareti, başlık, sahne notu ve tırnak kullanma.
13. Son cümle kısa bir takip çağrısı olsun.

Örnek yapı:
Son dakika. Bu gelişme gündemde geniş yankı uyandırabilir. ... Takipte kal.

Haber başlığı: {title}
Haber özeti: {summary}
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
        blocked = ["Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet", "Odatv", "Gerçek İzmir", "Konya Postası"]
        for source in blocked:
            script = script.replace(source, "")
        script = re.sub(r"\s+", " ", script).strip()
        if not script.lower().startswith("son dakika"):
            script = "Son dakika. " + script
        if len(script) < 180:
            raise RuntimeError("Metin çok kısa")
        if script.count(".") < 3:
            raise RuntimeError("Metin haber akışı için zayıf")
        return script
    except Exception as exc:
        logger.warning("AI metni oluşmadı, profesyonel haber fallback kullanılıyor: %s", exc)
        return fallback_script(item)
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("Son dakika professional script patch applied")
