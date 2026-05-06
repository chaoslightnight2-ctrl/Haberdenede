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
    return title[:170]


def clean_news_summary_for_script(summary: str) -> str:
    summary = strip_html(summary or "")
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary[:360]


def fallback_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    if summary:
        detail = f"Haberde öne çıkan bilgi şu: {summary}."
    else:
        detail = "Henüz tüm ayrıntılar netleşmiş değil ama başlık şimdiden dikkat çekiyor."
    return (
        f"Bu gelişme Türkiye gündemine bomba gibi düştü. {title}. "
        f"{detail} "
        "Asıl dikkat çeken nokta, bu olayın yalnızca tek bir başlık olarak kalmayıp gün içinde daha da büyüyebilecek olması. "
        "Şimdi gözler gelecek yeni açıklamalarda. Gelişmeler için takipte kal."
    )

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    prompt = f"""
Sen Türkçe YouTube Shorts için profesyonel haber spikeri gibi metin yazan bir editörsün.
Aşağıdaki haberden 35-45 saniyelik, mantıklı, akıcı ve sürükleyici bir haber metni yaz.

Zorunlu stil:
- İlk cümle clickbait hook olsun; merak uyandırsın.
- Hook güçlü olabilir ama haberi çarpıtma.
- Metnin geri kalanı haber diliyle mantıklı açıklasın.
- Kısa, net, konuşma diline uygun cümleler kullan.
- Bilgi uydurma, tarih/sayı/isim ekleme.
- Kaynakta olmayan iddiayı kesinmiş gibi yazma.
- Deprem, kaza, ölüm, afet gibi hassas haberlerde abartıyı azalt ve saygılı ol.
- Metin tek parça olsun, madde işareti veya emoji olmasın.
- Son cümle takip çağrısı olsun.

Örnek ton:
"Bu gelişme Türkiye gündemine bomba gibi düştü. Çünkü olayın arkasındaki detay, ilk bakışta göründüğünden daha önemli olabilir."

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
        if len(script) < 170:
            raise RuntimeError("Metin çok kısa")
        if "madde" in script.lower()[:50] or script.count("\n") > 2:
            raise RuntimeError("Metin formatı uygun değil")
        return script
    except Exception as exc:
        logger.warning("AI metni oluşmadı, kaliteli haber fallback kullanılıyor: %s", exc)
        return fallback_script(item)
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("Improved clickbait news script patch applied")
