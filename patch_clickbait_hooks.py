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
    return summary[:5000]


def get_best_news_content_for_script(item: dict[str, Any]) -> str:
    article = clean_news_summary_for_script(item.get("article_text", ""))
    summary = clean_news_summary_for_script(item.get("summary", ""))
    title = clean_news_title_for_script(item.get("title", ""))
    if article and len(article.split()) >= 45:
        return article[:5000]
    if summary and len(summary.split()) >= 35 and normalize_text(summary) != normalize_text(title):
        return summary[:2000]
    return ""


def make_clickbait_hook(title: str) -> str:
    title = clean_news_title_for_script(title)
    title = re.sub(r"[.!?]+$", "", title).strip()
    if not title:
        return "Bu gelişme sosyal medyada çok konuşulabilir."
    return f"Bu gelişme sosyal medyada çok konuşulabilir: {title}."


def clean_generated_text(text: str) -> str:
    text = strip_html(text or "")
    blocked = [
        "Google News", "Google Haberler", "RSS", "derlenen", "kapsamlı haber", "Haberin içeriğine göre",
        "Son dakika", "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Odatv", "Gerçek İzmir", "Konya Postası", "Anadolu Ajansı", "Kaynak", "Özet:"
    ]
    for source in blocked:
        text = re.sub(re.escape(source), "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .-|:")
    return text


def word_count_tr(text: str) -> int:
    return len([w for w in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", text or "") if w.strip()])


def is_generic_or_empty_script(script: str) -> bool:
    low = normalize_text(script)
    banned = [
        "google haber", "google news", "rss", "derlenen", "kapsamlı haber", "kapsamlı bilgiler",
        "haber içeriğine göre", "ayrıntılar sınırlı", "yeni açıklamalar", "resmi açıklamalar",
        "gelişmeler takip", "gelişmeleri aktarmaya devam", "konuya ilişkin detaylar", "detaylar netleşecek",
    ]
    if any(x in low for x in banned):
        return True
    return word_count_tr(script) < 35


def summarize_article_with_groq(title: str, content: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY GitHub Secrets içinde yok")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = f"""
Aşağıdaki haber metnini Türkçe olarak 45-50 kelimelik tek paragraf halinde özetle.

Kurallar:
- Sadece haber içeriğindeki bilgileri kullan.
- Uydurma bilgi, yorum, tahmin ekleme.
- Kaynak/site adı söyleme.
- Google News, RSS, derlenen haber, kapsamlı haber, haberin içeriğine göre ifadelerini kullanma.
- Aynı cümleyi veya aynı anlamı tekrar etme.
- Kim, ne yaptı, nerede oldu, varsa sayı/karar/iddia ne, net anlat.
- Clickbait hook yazma; sadece haber özetini yaz.
- 45 kelimeden kısa, 50 kelimeden uzun olmasın.

Başlık: {title}
Haber metni: {content[:5000]}
"""
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Sen Türkçe haber özetleyen profesyonel bir editörsün."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 180,
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    summary = clean_generated_text(data["choices"][0]["message"]["content"])
    wc = word_count_tr(summary)
    if wc < 35:
        raise RuntimeError(f"Groq özeti çok kısa: {wc} kelime")
    if wc > 65:
        words = re.findall(r"\S+", summary)
        summary = " ".join(words[:50]).strip(" .")
    return summary.strip(" .") + "."


def fallback_script(item: dict[str, Any]) -> str:
    raise RuntimeError("Groq olmadan metin üretilmeyecek; kalite için GROQ_API_KEY gerekli")

'''
s = s[:fallback_start] + new_fallback + s[fallback_end + 1:]

gen_start = s.index("def generate_news_script(")
gen_end = s.index("\n\nasync def create_voiceover(", gen_start)
new_generate = r'''def generate_news_script(item: dict[str, Any]) -> str:
    title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Haber içeriği yetersiz, video metni üretilmeyecek: {title}")

    hook = make_clickbait_hook(title)
    summary = summarize_article_with_groq(title, content)
    follow = "Daha fazlası için takipte kal."
    script = f"{hook} {summary} {follow}"
    script = clean_generated_text(script)
    if is_generic_or_empty_script(script):
        raise RuntimeError("Groq sonrası metin genel veya boş kaldı")
    logger.info("Groq ile haber metni üretildi: %s kelime", word_count_tr(script))
    return script
'''
s = s[:gen_start] + new_generate + s[gen_end:]

p.write_text(s, encoding="utf-8")
print("Groq 45-50 word article summary script patch applied")
