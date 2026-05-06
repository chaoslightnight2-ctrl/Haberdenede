from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

insert_at = s.index("\ndef fallback_script(")
article_block = r'''
def clean_article_text(text: str) -> str:
    text = strip_html(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    blocked_sources = [
        "Habertürk", "Sabah", "Yeni Şafak", "NTV", "CNN Türk", "Hürriyet", "Milliyet",
        "Sözcü", "Odatv", "Gerçek İzmir", "Konya Postası Gazetesi", "Anadolu Ajansı",
        "TRT Haber", "T24", "Gazete Duvar", "Cumhuriyet", "En Son Haber", "İHA", "DHA"
    ]
    for source in blocked_sources:
        text = text.replace(source, "")
    remove_phrases = [
        "Son Dakika Haberleri", "Video videosunu izle", "Haberi Görüntüle", "Devamını Oku",
        "Abone Ol", "Giriş Yap", "Kaydol", "Reklam", "Çerez", "Cookie", "KVKK",
    ]
    for phrase in remove_phrases:
        text = re.sub(re.escape(phrase), " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .-|:")


def score_article_text(text: str, title: str) -> int:
    norm = normalize_text(text)
    title_norm = normalize_text(title)
    if not norm:
        return 0
    score = min(len(norm), 1600) // 20
    if title_norm and norm == title_norm:
        score -= 80
    if len(norm.split()) < 35:
        score -= 40
    bad = ["çerez", "cookie", "abonelik", "reklam", "gizlilik", "whatsapp", "telegram", "facebook", "twitter", "instagram"]
    score -= sum(20 for word in bad if word in norm)
    return score


def extract_json_ld_article_body(html_text: str) -> str:
    chunks = []
    scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html_text, flags=re.I)
    for raw in scripts:
        try:
            raw = html.unescape(raw).strip()
            data = json.loads(raw)
            queue = data if isinstance(data, list) else [data]
            while queue:
                obj = queue.pop(0)
                if isinstance(obj, dict):
                    body = obj.get("articleBody") or obj.get("description")
                    if body:
                        chunks.append(str(body))
                    graph = obj.get("@graph")
                    if isinstance(graph, list):
                        queue.extend(graph)
                elif isinstance(obj, list):
                    queue.extend(obj)
        except Exception:
            continue
    return clean_article_text(" ".join(chunks))


def extract_meta_content(html_text: str) -> str:
    matches = re.findall(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|twitter:description)["\'][^>]+content=["\']([^"\']+)["\']',
        html_text,
        flags=re.I,
    )
    if not matches:
        matches = re.findall(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description|twitter:description)["\']',
            html_text,
            flags=re.I,
        )
    return clean_article_text(" ".join(matches))


def extract_paragraph_text(html_text: str) -> str:
    html_text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.I)
    html_text = re.sub(r"<style[\s\S]*?</style>", " ", html_text, flags=re.I)
    selectors = [
        r"<article[^>]*>([\s\S]*?)</article>",
        r"<main[^>]*>([\s\S]*?)</main>",
        r"<div[^>]+class=[\"'][^\"']*(?:article|content|news|detail|story|body)[^\"']*[\"'][^>]*>([\s\S]*?)</div>",
    ]
    candidate_html = []
    for pattern in selectors:
        candidate_html.extend(re.findall(pattern, html_text, flags=re.I))
    if not candidate_html:
        candidate_html = [html_text]

    cleaned = []
    blocked = [
        "çerez", "cookie", "abonelik", "reklam", "gizlilik", "kullanım şartları",
        "whatsapp", "telegram", "facebook", "twitter", "instagram", "x hesabı",
        "yorumlar", "sıradaki haber", "en çok okunan", "son dakika haberleri",
    ]
    for block in candidate_html[:6]:
        paragraphs = re.findall(r"<(?:p|h2|h3|li)[^>]*>([\s\S]*?)</(?:p|h2|h3|li)>", block, flags=re.I)
        for paragraph in paragraphs:
            text = clean_article_text(paragraph)
            low = normalize_text(text)
            if len(text) < 45:
                continue
            if any(word in low for word in blocked):
                continue
            if text in cleaned:
                continue
            cleaned.append(text)
            if len(" ".join(cleaned)) > 2200:
                break
        if len(" ".join(cleaned)) > 2200:
            break
    return clean_article_text(" ".join(cleaned))


def fetch_url_text(url: str, item: dict[str, Any]) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    }
    response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    response.raise_for_status()
    item["resolved_url"] = response.url
    html_text = response.text or ""
    parts = [
        extract_json_ld_article_body(html_text),
        extract_meta_content(html_text),
        extract_paragraph_text(html_text),
    ]
    return clean_article_text(" ".join(part for part in parts if part))[:2400]


def fetch_article_content(item: dict[str, Any]) -> str:
    title = item.get("title", "")
    candidates = []
    if item.get("url"):
        candidates.append(item["url"])
    # Google News bağlantısı gerçek içeriği vermezse başlıkla Google News araması yerine RSS özeti ve meta içerik birlikte kullanılır.
    best = ""
    best_score = -999
    for url in dict.fromkeys(candidates):
        try:
            text = fetch_url_text(url, item)
            score = score_article_text(text, title)
            logger.info("İçerik adayı skor=%s uzunluk=%s url=%s", score, len(text), url[:80])
            if score > best_score:
                best = text
                best_score = score
        except Exception as exc:
            logger.warning("Haber içeriği çekilemedi: %s", exc)

    rss_text = clean_article_text(" ".join([item.get("summary", ""), item.get("title", "")]))
    if score_article_text(rss_text, title) > best_score:
        best = rss_text
        best_score = score_article_text(rss_text, title)

    if best_score < 15:
        logger.warning("Haber içeriği hala zayıf: skor=%s başlık=%s", best_score, title[:90])
    return best[:2000]


def enrich_selected_with_article_content(selected: list[dict[str, Any]]) -> None:
    for item in selected:
        article_text = fetch_article_content(item)
        summary = item.get("summary", "")
        if article_text and len(normalize_text(article_text).split()) >= 35:
            item["article_text"] = article_text
            item["content_quality"] = "article_text"
            logger.info("Haber içeriği çekildi: %s karakter", len(article_text))
        else:
            item["article_text"] = article_text or summary
            item["content_quality"] = "weak_content"
            logger.warning("Haber içeriği zayıf kaldı: %s", item.get("title", "")[:90])

'''
# Eski article patch blokları tekrar eklenirse sorun olmaması için mevcut fonksiyon adından önceki son eklemeyi kullanır.
s = s[:insert_at] + article_block + s[insert_at:]

old = "selected = choose_top_three(news_pool, history)\n    save_json(SELECTED_FILE, {\"generated_at\": now_tr().isoformat(), \"selected_news\": selected})"
new = "selected = choose_top_three(news_pool, history)\n    enrich_selected_with_article_content(selected)\n    save_json(SELECTED_FILE, {\"generated_at\": now_tr().isoformat(), \"selected_news\": selected})"
s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
print("Stronger article content extraction patch applied")
