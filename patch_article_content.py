from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

insert_at = s.index("\ndef fallback_script(")
article_block = r'''
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
    return strip_html(" ".join(matches))


def extract_paragraph_text(html_text: str) -> str:
    html_text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.I)
    html_text = re.sub(r"<style[\s\S]*?</style>", " ", html_text, flags=re.I)
    paragraphs = re.findall(r"<p[^>]*>([\s\S]*?)</p>", html_text, flags=re.I)
    cleaned = []
    blocked = [
        "çerez", "cookie", "abonelik", "reklam", "gizlilik", "kullanım şartları",
        "son dakika haberleri", "whatsapp", "telegram", "facebook", "twitter", "x hesabı",
    ]
    for paragraph in paragraphs:
        text = strip_html(paragraph)
        text = re.sub(r"\s+", " ", text).strip()
        low = normalize_text(text)
        if len(text) < 45:
            continue
        if any(word in low for word in blocked):
            continue
        cleaned.append(text)
        if len(" ".join(cleaned)) > 1400:
            break
    return " ".join(cleaned)


def fetch_article_content(item: dict[str, Any]) -> str:
    url = item.get("url", "")
    if not url:
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
        }
        response = requests.get(url, headers=headers, timeout=18, allow_redirects=True)
        response.raise_for_status()
        final_url = response.url
        html_text = response.text or ""
        content = extract_paragraph_text(html_text)
        meta = extract_meta_content(html_text)
        combined = " ".join(x for x in [meta, content] if x)
        combined = strip_html(combined)
        combined = re.sub(r"\s+", " ", combined).strip()
        if final_url:
            item["resolved_url"] = final_url
        return combined[:1800]
    except Exception as exc:
        logger.warning("Haber içeriği çekilemedi: %s", exc)
        return ""


def enrich_selected_with_article_content(selected: list[dict[str, Any]]) -> None:
    for item in selected:
        article_text = fetch_article_content(item)
        if article_text and len(article_text) > len(item.get("summary", "")):
            item["article_text"] = article_text
            item["content_quality"] = "article_text"
            logger.info("Haber içeriği çekildi: %s karakter", len(article_text))
        else:
            item["article_text"] = ""
            item["content_quality"] = "rss_only"
            logger.warning("Haber içeriği zayıf kaldı, RSS özeti kullanılacak: %s", item.get("title", "")[:90])

'''
s = s[:insert_at] + article_block + s[insert_at:]

old = "selected = choose_top_three(news_pool, history)\n    save_json(SELECTED_FILE, {\"generated_at\": now_tr().isoformat(), \"selected_news\": selected})"
new = "selected = choose_top_three(news_pool, history)\n    enrich_selected_with_article_content(selected)\n    save_json(SELECTED_FILE, {\"generated_at\": now_tr().isoformat(), \"selected_news\": selected})"
s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
print("Article content extraction patch applied")
