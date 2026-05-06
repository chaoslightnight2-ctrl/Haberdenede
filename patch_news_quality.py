from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

news_start = s.index("NEWS_QUERIES = [")
news_end = s.index("]\n\nBACKGROUND_HINTS", news_start) + 1
new_news_queries = '''NEWS_QUERIES = [
    "Türkiye son dakika flaş gelişme",
    "Türkiye gündem sıcak gelişme",
    "Türkiye ekonomi kriz enflasyon zam dolar",
    "Türkiye siyaset Erdoğan meclis bakan karar",
    "Türkiye adliye operasyon gözaltı tutuklama dava",
    "Türkiye afet yangın sel kaza deprem",
    "Türkiye spor transfer derbi maç son dakika",
    "Türkiye sosyal medya gündem viral olay",
]
'''
s = s[:news_start] + new_news_queries + s[news_end:]

ks_start = s.index("def keyword_score(")
ks_end = s.index("\ndef recency_score(", ks_start)
new_keyword_score = r'''def is_low_value_news(item: dict[str, Any]) -> bool:
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    low_value_patterns = [
        "deprem mi oldu",
        "nerede oldu",
        "son depremler listesi",
        "kandilli ve afad",
        "hava durumu",
        "bugün hava",
        "namaz vakti",
        "hangi kanalda",
        "saat kaçta",
        "canlı izle",
        "altın fiyatları ne kadar",
        "dolar kaç tl",
        "burç yorumları",
    ]
    if any(pattern in text for pattern in low_value_patterns):
        return True
    title = normalize_text(item.get("title", ""))
    if title.count("?") >= 2:
        return True
    if len(title.split()) > 24:
        return True
    return False


def keyword_score(text: str) -> int:
    text_n = normalize_text(text)
    weights = {
        "son dakika": 14,
        "flaş": 12,
        "kriz": 11,
        "istifa": 10,
        "tutuklandı": 10,
        "gözaltı": 9,
        "operasyon": 9,
        "yasak": 9,
        "zam": 9,
        "enflasyon": 9,
        "faiz": 8,
        "dolar": 7,
        "borsa": 6,
        "deprem": 8,
        "yangın": 8,
        "sel": 8,
        "kaza": 7,
        "mahkeme": 7,
        "dava": 7,
        "karar": 7,
        "meclis": 6,
        "bakan": 6,
        "cumhurbaşkan": 7,
        "erdoğan": 7,
        "seçim": 8,
        "açıklama": 5,
        "soruşturma": 8,
        "iddia": 6,
        "görüntü": 7,
        "sosyal medya": 7,
        "viral": 7,
        "transfer": 6,
        "derbi": 6,
        "istanbul": 4,
        "ankara": 3,
        "izmir": 3,
        "türkiye": 2,
    }
    score = sum(weight for word, weight in weights.items() if word in text_n)

    curiosity_words = ["neden", "nasıl", "ne oldu", "ortaya çıktı", "ilk kez", "dakika dakika", "kritik"]
    score += sum(3 for word in curiosity_words if word in text_n)

    boring_words = ["listesi", "kaçta", "hangi kanalda", "hava durumu", "namaz", "burç", "son depremler"]
    score -= sum(10 for word in boring_words if word in text_n)
    return score
'''
s = s[:ks_start] + new_keyword_score + s[ks_end:]

choose_start = s.index("def choose_top_three(")
choose_end = s.index("\ndef fallback_script(", choose_start)
new_choose = r'''def choose_top_three(news: list[dict[str, Any]], history: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    ranked = enrich_and_rank(news)

    # Önce SEO/çok sıkıcı haberleri at. Yeterli haber kalmazsa aşağıda gevşetiriz.
    quality_ranked = [item for item in ranked if not is_low_value_news(item)]
    if len(quality_ranked) < 8:
        quality_ranked = ranked

    for item in quality_ranked:
        if in_history(item, history.get("processed_news", [])):
            continue
        if too_similar_to_selected(item, selected):
            continue
        if item.get("viral_score", 0) < 10 and len(selected) < 2:
            continue
        selected.append(item)
        if len(selected) == 3:
            break

    if len(selected) < 3:
        for item in ranked:
            if item in selected:
                continue
            if in_history(item, history.get("processed_news", [])):
                continue
            if too_similar_to_selected(item, selected):
                continue
            selected.append(item)
            if len(selected) == 3:
                break

    if len(selected) < 3:
        raise RuntimeError("3 farklı ve yeterince güçlü haber seçilemedi.")
    return selected
'''
s = s[:choose_start] + new_choose + s[choose_end:]

p.write_text(s, encoding="utf-8")
print("News quality patch applied")
