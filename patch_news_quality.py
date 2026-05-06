from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

news_start = s.index("NEWS_QUERIES = [")
news_end = s.index("]\n\nBACKGROUND_HINTS", news_start) + 1
new_news_queries = '''NEWS_QUERIES = [
    "son dakika Türkiye",
    "flaş haber Türkiye",
    "gündem Türkiye son dakika",
    "Türkiye viral olay",
    "sosyal medya gündem Türkiye",
    "Türkiye operasyon gözaltı tutuklama",
    "Türkiye adliye mahkeme karar",
    "Türkiye ekonomi zam enflasyon kriz",
    "Türkiye siyaset meclis bakan karar",
    "Erdoğan açıklama son dakika",
    "İstanbul son dakika olay",
    "Ankara son dakika olay",
    "İzmir son dakika olay",
    "Türkiye deprem yangın sel kaza",
    "Türkiye spor transfer istifa kriz",
    "Türkiye herkes bunu konuşuyor",
    "Türkiye gündemi karıştıran olay",
]
'''
s = s[:news_start] + new_news_queries + s[news_end:]

ks_start = s.index("def keyword_score(")
ks_end = s.index("\ndef recency_score(", ks_start)
new_keyword_score = r'''def is_low_value_news(item: dict[str, Any]) -> bool:
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    title = normalize_text(item.get("title", ""))
    low_value_patterns = [
        "deprem mi oldu", "nerede oldu", "son depremler listesi", "kandilli ve afad",
        "hava durumu", "bugün hava", "namaz vakti", "hangi kanalda", "saat kaçta",
        "canlı izle", "canlı yayın", "altın fiyatları ne kadar", "dolar kaç tl",
        "burç yorumları", "piyango sonuçları", "çekiliş sonuçları", "tv yayın akışı",
        "maç hangi kanalda", "şifresiz mi", "kaçta başlayacak", "video videosunu izle",
        "foto galeri", "galeri", "test çöz", "listele", "günlük burç",
    ]
    if any(pattern in text for pattern in low_value_patterns):
        return True
    if title.count("?") >= 2:
        return True
    words = title.split()
    if len(words) < 4 or len(words) > 24:
        return True
    # Başlık sadece fiyat/saat/listeden ibaretse Shorts için zayıf.
    weak_tokens = {"liste", "listesi", "fiyat", "fiyatları", "kaç", "nerede", "hangi", "bugün"}
    if len([w for w in words if w in weak_tokens]) >= 2:
        return True
    return False


def source_name_from_title(title: str) -> str:
    raw = strip_html(title or "")
    if " - " in raw:
        return raw.rsplit(" - ", 1)[-1].strip().lower()
    return ""


def title_quality_score(title: str) -> int:
    clean = normalize_text(title)
    words = clean.split()
    score = 0
    if 6 <= len(words) <= 15:
        score += 12
    elif 4 <= len(words) <= 20:
        score += 6
    else:
        score -= 12

    if any(x in clean for x in ["son dakika", "flaş", "kriz", "şok", "ortaya çıktı", "gündem oldu", "herkes bunu konuşuyor"]):
        score += 10
    if any(x in clean for x in ["iddia", "karar", "açıklama", "görüntü", "soruşturma", "operasyon", "gözaltı", "tutuklama"]):
        score += 10
    if "?" in title:
        score -= 10
    if title.count("|") >= 1:
        score -= 8
    if title.count(":") >= 1:
        score += 3
    return score


def keyword_score(text: str) -> int:
    text_n = normalize_text(text)
    weights = {
        "son dakika": 15, "flaş": 14, "kriz": 14, "şok": 10, "skandal": 13,
        "istifa": 13, "tutuklandı": 13, "tutuklama": 12, "gözaltı": 11,
        "operasyon": 11, "soruşturma": 11, "yasak": 10, "ceza": 8,
        "iddia": 9, "görüntü": 10, "ortaya çıktı": 10, "karar": 9,
        "zam": 10, "enflasyon": 9, "faiz": 8, "dolar": 7, "borsa": 5,
        "deprem": 8, "yangın": 8, "sel": 8, "kaza": 7,
        "mahkeme": 8, "dava": 8, "meclis": 7, "bakan": 7,
        "cumhurbaşkan": 8, "erdoğan": 8, "seçim": 9,
        "sosyal medya": 10, "viral": 10, "gündem oldu": 12, "herkes bunu konuşuyor": 12,
        "transfer": 7, "derbi": 7, "istifa kararı": 12,
        "istanbul": 4, "ankara": 4, "izmir": 4, "türkiye": 2,
    }
    score = sum(weight for word, weight in weights.items() if word in text_n)
    curiosity_words = ["neden", "nasıl", "ne oldu", "ortaya çıktı", "ilk kez", "kritik", "perde arkası", "dikkat çeken"]
    score += sum(4 for word in curiosity_words if word in text_n)
    boring_words = ["listesi", "kaçta", "hangi kanalda", "hava durumu", "namaz", "burç", "son depremler", "fiyatları"]
    score -= sum(14 for word in boring_words if word in text_n)
    return score
'''
s = s[:ks_start] + new_keyword_score + s[ks_end:]

enrich_start = s.index("def enrich_and_rank(")
enrich_end = s.index("\ndef in_history(", enrich_start)
new_enrich = r'''def enrich_and_rank(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Aynı olay birçok kaynakta geçiyorsa bu olayın gündem/viral gücü artar.
    clusters: list[dict[str, Any]] = []
    for item in news:
        placed = False
        for cluster in clusters:
            if similarity(item.get("title", ""), cluster["title"]) >= 0.62:
                cluster["items"].append(item)
                placed = True
                break
        if not placed:
            clusters.append({"title": item.get("title", ""), "items": [item]})

    cluster_strength: dict[str, int] = {}
    for cluster in clusters:
        sources = {source_name_from_title(x.get("title", "")) or x.get("query", "") for x in cluster["items"]}
        strength = min(len(cluster["items"]), 8) * 3 + min(len(sources), 5) * 4
        for x in cluster["items"]:
            cluster_strength[x["fingerprint"]] = strength

    for item in news:
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = title + " " + summary
        score = recency_score(item["published_at"])
        score += keyword_score(text)
        score += title_quality_score(title)
        score += cluster_strength.get(item["fingerprint"], 0)

        if is_low_value_news(item):
            score -= 80
        if len(summary) > 180:
            score += 5
        if len(summary) < 45:
            score -= 8

        # Adliye/operasyon haberleri viral olabilir ama 3 videonun tamamını kaplamasın diye seçme aşamasında çeşitlilik de uygulanacak.
        item["viral_score"] = round(score, 2)
        item["topic_bucket"] = detect_topic_bucket(item)
        item["source_name"] = source_name_from_title(title)
    return sorted(news, key=lambda x: x["viral_score"], reverse=True)


def detect_topic_bucket(item: dict[str, Any]) -> str:
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    if any(w in text for w in ["operasyon", "gözaltı", "tutuk", "mahkeme", "dava", "soruşturma"]):
        return "adliye"
    if any(w in text for w in ["zam", "enflasyon", "faiz", "dolar", "borsa", "ekonomi"]):
        return "ekonomi"
    if any(w in text for w in ["meclis", "bakan", "erdoğan", "cumhurbaşkan", "seçim", "siyaset"]):
        return "siyaset"
    if any(w in text for w in ["deprem", "yangın", "sel", "kaza", "afet"]):
        return "afet"
    if any(w in text for w in ["spor", "futbol", "transfer", "derbi", "maç"]):
        return "spor"
    if any(w in text for w in ["sosyal medya", "viral", "gündem oldu", "herkes bunu konuşuyor"]):
        return "sosyal"
    return "genel"
'''
s = s[:enrich_start] + new_enrich + s[enrich_end:]

choose_start = s.index("def choose_top_three(")
choose_end = s.index("\ndef fallback_script(", choose_start)
new_choose = r'''def choose_top_three(news: list[dict[str, Any]], history: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = enrich_and_rank(news)
    if len(ranked) < 3:
        raise RuntimeError(f"Yeterli haber bulunamadı. Bulunan haber sayısı: {len(ranked)}")

    candidates = [item for item in ranked if not is_low_value_news(item)]
    if len(candidates) < 8:
        candidates = ranked

    selected: list[dict[str, Any]] = []
    used_topics: dict[str, int] = {}
    used_sources: set[str] = set()

    def can_take(item: dict[str, Any], strict: bool = True) -> bool:
        if in_history(item, history.get("processed_news", [])):
            return False
        if too_similar_to_selected(item, selected):
            return False
        topic = item.get("topic_bucket", "genel")
        source = item.get("source_name", "")
        if strict:
            if used_topics.get(topic, 0) >= 1 and len(selected) < 2:
                return False
            if used_topics.get(topic, 0) >= 2:
                return False
            if source and source in used_sources:
                return False
            if item.get("viral_score", 0) < 18:
                return False
        return True

    # 1. tur: en yüksek viral skor + konu/kaynak çeşitliliği.
    for item in candidates[:120]:
        if can_take(item, strict=True):
            selected.append(item)
            used_topics[item.get("topic_bucket", "genel")] = used_topics.get(item.get("topic_bucket", "genel"), 0) + 1
            if item.get("source_name"):
                used_sources.add(item["source_name"])
        if len(selected) == 3:
            break

    # 2. tur: kaynak/konu kısıtını gevşet ama tekrar ve history elemesi kalsın.
    if len(selected) < 3:
        for item in candidates[:180]:
            if item in selected:
                continue
            if can_take(item, strict=False):
                selected.append(item)
            if len(selected) == 3:
                break

    # 3. tur: History çok sıkıysa sadece benzerlik elemesiyle doldur.
    if len(selected) < 3:
        for item in candidates:
            if item in selected:
                continue
            if too_similar_to_selected(item, selected):
                continue
            selected.append(item)
            if len(selected) == 3:
                break

    if len(selected) < 3:
        raise RuntimeError("3 farklı ve tıklanma potansiyeli yüksek haber seçilemedi.")

    logger.info("Seçilen viral haberler:")
    for item in selected:
        logger.info("score=%s topic=%s source=%s title=%s", item.get("viral_score"), item.get("topic_bucket"), item.get("source_name"), item.get("title"))
    return selected
'''
s = s[:choose_start] + new_choose + s[choose_end:]

p.write_text(s, encoding="utf-8")
print("Improved viral news ranking patch applied")
