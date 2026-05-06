from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

fallback_start = s.index("def fallback_script(")
fallback_end = s.index("\ndef generate_news_script(", fallback_start)
new_fallback = r'''def fallback_script(item: dict[str, Any]) -> str:
    title = item.get("title", "").strip()
    summary = item.get("summary", "").strip()[:280]
    return (
        f"Bu gelişme Türkiye gündemine bomba gibi düştü. {title}. "
        f"İlk bakışta sıradan gibi görünebilir ama detaylar oldukça dikkat çekici. {summary}. "
        "Şimdi herkes aynı soruyu soruyor: Bu olayın devamında ne olacak? Gelişmeleri kaçırmamak için takipte kal."
    )

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    prompt = f"""
Sen Türkçe YouTube Shorts için viral haber anlatımı yazan agresif bir editörsün.
Aşağıdaki haber bilgisini kullanarak 35-45 saniyelik, clickbait tadında ama gerçeği çarpıtmayan bir Shorts metni yaz.

Stil:
- İlk cümle çok güçlü bir hook olsun.
- Hook örnekleri gibi yaz ama birebir kopyalama:
  "Bu olay Türkiye'de gündemi karıştırdı."
  "Kimse bunu beklemiyordu."
  "Bu detay ortaya çıkınca herkes aynı soruyu sordu."
  "Görünenden çok daha büyük bir gelişme olabilir."
  "Sosyal medyada herkes bunu konuşuyor."
- Merak duygusu yüksek olsun.
- Cümleler kısa, hızlı, vurucu ve seslendirmeye uygun olsun.
- Abartılı anlatım olabilir ama bilgi uydurma.
- Kesin olmayan iddiaları kesinmiş gibi söyleme.
- Şiddet, felaket veya ölüm haberlerinde saygılı ve sorumlu kal.
- Emoji, madde işareti, başlık ve sahne notu yazma.
- Tek parça konuşma metni ver.
- Son cümle takip çağrısı olsun.

Haber başlığı: {item['title']}
Haber özeti: {item.get('summary', '')}
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
        if len(script) < 140:
            raise RuntimeError("Metin çok kısa")
        return script
    except Exception as exc:
        logger.warning("AI metni oluşmadı, clickbait fallback kullanılıyor: %s", exc)
        return fallback_script(item)
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("Clickbait hook patch applied")
