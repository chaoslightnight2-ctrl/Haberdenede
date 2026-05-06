from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

fallback_start = s.index("def fallback_script(")
fallback_end = s.index("\ndef generate_news_script(", fallback_start)
new_fallback = r'''def clean_news_title_for_script(title: str) -> str:
    title = strip_html(title or "")
    title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
    title = re.sub(r"(?i)son dakika[:\s-]*", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip()
    return title[:155]


def clean_news_summary_for_script(summary: str) -> str:
    summary = strip_html(summary or "")
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary[:420]


def fallback_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    detail = f"Haberde öne çıkan bilgi şu: {summary}." if summary else "Resmi ayrıntılar netleştikçe başlığın etkisi daha iyi anlaşılacak."
    return (
        f"Bu gelişme Türkiye gündemine bomba gibi düştü. {title}. "
        f"{detail} "
        "Konu yalnızca tek bir başlıktan ibaret değil; kararın, açıklamanın ya da gelişmenin gün içinde yeni sonuçlar doğurması bekleniyor. "
        "Biz de gelişmeleri takip edip aktarmaya devam edeceğiz. Yeni haberler için takipte kal."
    )

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    prompt = f"""
Sen deneyimli bir Türkçe haber spikerisin ve YouTube Shorts için profesyonel haber metni yazıyorsun.
Aşağıdaki haberden 35-45 saniyelik tek parça konuşma metni yaz.

Kesin kurallar:
- İlk cümle clickbait hook olsun ve dikkat çeksin.
- Hook güçlü olsun ama haberin anlamını bozmasın.
- Hooktan sonra metin profesyonel haber diliyle devam etsin.
- Gereksiz abartı, tekrar, yapay heyecan ve boş cümle kullanma.
- Verilen başlık ve özet dışında bilgi, tarih, kişi, sayı veya iddia uydurma.
- Kaynakta kesin olmayan şeyi kesinmiş gibi söyleme.
- Olayın neden önemli olabileceğini mantıklı biçimde açıkla.
- Cümleler kısa, akıcı ve seslendirmeye uygun olsun.
- Deprem, afet, kaza, ölüm, adliye haberlerinde saygılı ve ölçülü kal.
- Emoji, madde işareti, başlık, sahne notu ve tırnak kullanma.
- Son cümle kısa bir takip çağrısı olsun.

İyi başlangıç örnekleri:
Bu gelişme Türkiye gündemine bomba gibi düştü.
Bu detay ortaya çıkınca herkes aynı soruyu sordu.
Görünenden çok daha önemli bir gelişme olabilir.
Bu haber gün içinde daha çok konuşulacak gibi görünüyor.

Haber başlığı: {title}
Haber özeti: {summary}
Kaynak: {item.get('source', '')}
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
print("Professional news script patch applied")
