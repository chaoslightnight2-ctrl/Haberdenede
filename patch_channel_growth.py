"""Haberdenede kanal kapsamı, içerik paketlemesi ve güvenli üretim yedeği."""
from pathlib import Path
import re

MAIN = Path("main.py")
source = MAIN.read_text(encoding="utf-8")

queries = '''NEWS_QUERIES = [
    "Türkiye son dakika haberleri",
    "Türkiye gündem günün gelişmeleri",
    "Türkiye ekonomi enflasyon faiz bütçe piyasalar",
    "Türkiye tüketici fiyatları vergi maaş emekli",
    "Türkiye konut kira şehircilik belediye",
    "Türkiye eğitim okul üniversite sınav",
    "Türkiye sağlık hastane ilaç halk sağlığı",
    "Türkiye bilim araştırma uzay keşif",
    "Türkiye teknoloji yapay zeka dijital siber güvenlik",
    "Türkiye enerji elektrik doğal gaz yenilenebilir",
    "Türkiye iklim çevre su kuraklık hava",
    "Türkiye ulaşım trafik demiryolu havacılık",
    "Türkiye şehirler yerel haber altyapı",
    "Türkiye adliye hukuk mahkeme karar",
    "Türkiye siyaset meclis kamu politikası",
    "Türkiye diplomasi dış politika dünya",
    "dünyada bugün önemli gelişmeler Türkiye",
    "Avrupa dünya ekonomi teknoloji haberleri",
    "Türkiye kültür sanat sinema müzik kitap",
    "Türkiye spor futbol basketbol voleybol",
    "Türkiye sosyal yaşam toplum dikkat çeken gelişmeler",
    "Türkiye dijital kültür sosyal medya gündem",
]
'''
source, count = re.subn(r"NEWS_QUERIES\s*=\s*\[[\s\S]*?\]\s*", queries + "\n", source, count=1)
if count != 1:
    raise RuntimeError("NEWS_QUERIES alanı bulunamadı; kapsam güncellemesi uygulanmadı.")

marker = "# HABERDENEDE_CHANNEL_GROWTH_PATCH"
if marker not in source:
    block = r'''

# HABERDENEDE_CHANNEL_GROWTH_PATCH
# YouTube önerileri için konu kapsamı geniş tutulur; seçimde tek bir gündem türünün
# üç slotu da kaplaması önlenir. Kaynakta olmayan iddia/yorum üretilmez.
def detect_topic_bucket(item):
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    groups = [
        ("bilim_teknoloji", ["yapay zeka", "teknoloji", "siber", "uygulama", "internet", "bilim", "araştırma", "uzay", "uydu", "robot", "çip"]),
        ("ekonomi_yasam", ["ekonomi", "enflasyon", "faiz", "bütçe", "vergi", "maaş", "emekli", "zam", "fiyat", "kira", "konut", "tüketici", "işçi"]),
        ("sağlık_eğitim", ["sağlık", "hastane", "ilaç", "doktor", "eğitim", "üniversite", "okul", "öğrenci", "sınav"]),
        ("iklim_enerji", ["iklim", "çevre", "kuraklık", "su seviyesi", "enerji", "elektrik", "doğal gaz", "orman", "hava kirliliği"]),
        ("ulaşım_şehir", ["ulaşım", "trafik", "metro", "demiryolu", "tren", "uçuş", "havalimanı", "belediye", "altyapı", "şehir"]),
        ("dünya_diplomasi", ["dış politika", "diplomasi", "uluslararası", "avrupa birliği", "nato", "ukrayna", "gazze", "abd", "dünya"]),
        ("kültür_sanat", ["kültür", "sanat", "sinema", "film", "müzik", "konser", "kitap", "festival", "müze"]),
        ("spor", ["spor", "futbol", "basketbol", "voleybol", "maç", "transfer", "şampiyona", "olimpiyat"]),
        ("adliye_toplum", ["mahkeme", "yargıtay", "anayasa mahkemesi", "dava", "soruşturma", "gözaltı", "tutuk", "adliye", "toplum", "sosyal yaşam"]),
        ("siyaset_kamu", ["siyaset", "meclis", "bakan", "cumhurbaşkan", "erdoğan", "seçim", "parti", "kamu politikası"]),
        ("afet_güvenlik", ["deprem", "yangın", "sel", "fırtına", "afet", "kaza", "güvenlik"]),
    ]
    for bucket, words in groups:
        if any(word in text for word in words):
            return bucket
    return "gündem_genel"


_growth_original_enrich_and_rank = enrich_and_rank

def enrich_and_rank(news):
    ranked = _growth_original_enrich_and_rank(news)
    for item in ranked:
        item["topic_bucket"] = detect_topic_bucket(item)
        raw_score = float(item.get("viral_score", 0) or 0)
        try:
            keyword_part = float(keyword_score(item.get("title", "") + " " + item.get("summary", "")))
        except Exception:
            keyword_part = 0.0
        # Dampen sensational keyword stuffing while retaining recency, source consensus and specificity.
        item["viral_score"] = round(raw_score - keyword_part + max(-10.0, min(keyword_part, 22.0)), 2)
    return sorted(ranked, key=lambda item: item.get("viral_score", 0), reverse=True)


def choose_top_three(news, history):
    ranked = enrich_and_rank(news)
    processed = history.get("processed_news", [])
    eligible = [item for item in ranked if not is_low_value_news(item)]
    selected = []
    topic_counts = {}
    source_counts = {}

    def admissible(item, topic_limit, require_source_spread=False):
        if item in selected or in_history(item, processed):
            return False
        if too_similar_to_selected(item, selected):
            return False
        topic = item.get("topic_bucket", "gündem_genel")
        source = (item.get("source_name") or "").strip().lower()
        if topic_counts.get(topic, 0) >= topic_limit:
            return False
        if require_source_spread and source and source_counts.get(source, 0) >= 1:
            return False
        return True

    # First pass aims for three different topics and publishers.
    for item in eligible:
        if admissible(item, 1, True):
            selected.append(item)
            topic = item.get("topic_bucket", "gündem_genel")
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            source = (item.get("source_name") or "").strip().lower()
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1
            if len(selected) == 3:
                break

    # If today's news supply is concentrated, allow a second story from a topic.
    if len(selected) < 3:
        for item in eligible:
            if admissible(item, 2):
                selected.append(item)
                topic = item.get("topic_bucket", "gündem_genel")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                if len(selected) == 3:
                    break

    # Preserve the existing anti-repeat checks, but do not fail only because all
    # available stories happen to belong to the same topic.
    if len(selected) < 3:
        for item in ranked:
            if item in selected or in_history(item, processed):
                continue
            if not too_similar_to_selected(item, selected):
                selected.append(item)
            if len(selected) == 3:
                break
    if len(selected) < 3:
        raise RuntimeError("Tekrarsız üç haber bulunamadı.")
    logger.info("Konu çeşitliliğiyle seçilen haberler: %s", [(x.get("topic_bucket"), x.get("title")) for x in selected])
    return selected


def _growth_fallback_script(item, title, content):
    summary = clean_news_summary_for_script(item.get("summary", "") or "")
    if len(summary.split()) < 18:
        summary = clean_news_summary_for_script(content or "")
    if not summary:
        raise RuntimeError("Groq yanıt vermedi ve doğrulanabilir haber özeti bulunamadı; içerik uydurulmadı.")
    sentences = re.split(r"(?<=[.!?])\s+", summary)
    body = " ".join(sentences[:3]).strip()
    words = body.split()
    if len(words) > 62:
        body = " ".join(words[:62]).rstrip(" ,;:")
    script = clean_generated_text(f"Öne çıkan gelişme: {title}. {body}")
    if len(script.split()) > 76:
        script = " ".join(script.split()[:76]).rstrip(" ,;:")
    return script


def generate_news_script(item):
    source_title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Doğrulanabilir haber metni yetersiz; video üretilmedi: {source_title}")
    topic = detect_topic_bucket(item)
    prompt = f"""
Türkiye’den Haber adlı geniş kapsamlı haber kanalı için kısa video metadatası ve anlatımı üret.
Yalnızca aşağıdaki başlık ve haber metninde açıkça bulunan olguları kullan. İddiaları iddia olarak belirt;
kesinleşmemiş bilgiyi kesin hüküm gibi yazma. Kaynakta olmayan neden, sonuç, sayı, tarih veya yorum ekleme.
Giriş ilk cümlede somut gelişmeyi söylesin. Merak uyandır, fakat yanıltıcı/sansasyonel olma.
Anlatım 45-70 Türkçe kelime, tek paragraf ve doğal seslendirmeye uygun olsun. Açıklama 1-2 kısa,
özgün cümle olsun; haberi arayan kişinin konuyu anlayacağı ana terimleri doğal biçimde içersin.
Geçerli JSON dışında hiçbir şey döndürme:
{{"title":"en fazla 90 karakter, özgün ve doğru başlık","narration":"...","description":"..."}}

Kanal kapsamı/kategori: {topic}
Kaynak başlığı: {source_title}
Haber metni: {content[:4200]}
"""
    try:
        raw = groq_chat(prompt, max_tokens=420, temperature=0.2)
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("Model geçerli JSON döndürmedi.")
        data = json.loads(match.group(0))
        new_title = clean_generated_text(str(data.get("title", ""))).strip(" .-|:")
        narration = clean_generated_text(str(data.get("narration", ""))).strip()
        description = clean_generated_text(str(data.get("description", ""))).strip()
        if not new_title or not narration or not description:
            raise ValueError("Model başlık/anlatım/açıklama alanlarından birini boş bıraktı.")
        if len(new_title) > 90 or not 28 <= len(narration.split()) <= 78:
            raise ValueError("Model çıktısı uzunluk denetimini geçemedi.")
        item["source_headline"] = item.get("title", "")
        item["youtube_description"] = description
        logger.info("Kanal için özgün başlık ve anlatım üretildi: %s", new_title)
    except Exception as exc:
        response = getattr(exc, "response", None)
        detail = ""
        if response is not None:
            detail = re.sub(r"\s+", " ", str(getattr(response, "text", "")))[:350]
        logger.warning("Groq içerik üretimi başarısız; kaynakla sınırlı yedek anlatım kullanılıyor: %s %s", exc, detail)
        new_title = source_title[:90]
        item["source_headline"] = item.get("title", "")
        item["youtube_description"] = f"{source_title}. Haber ayrıntıları kaynak bağlantısında; bu kısa video mevcut kaynak metnini özetler."
        narration = _growth_fallback_script(item, source_title, content)

    item["title"] = new_title
    resolved = item.get("resolved_url", "")
    if resolved.startswith("https://") and "news.google.com" not in resolved:
        item["url"] = resolved
    return narration


def make_viral_tags(item):
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    tags = ["Türkiye'den Haber", "Türkiye haberleri"]
    for bucket, words in [
        ("bilim_teknoloji", ["teknoloji", "bilim", "yapay zeka", "siber güvenlik"]),
        ("ekonomi_yasam", ["ekonomi", "tüketici", "maaş", "enflasyon"]),
        ("sağlık_eğitim", ["sağlık", "eğitim"]),
        ("iklim_enerji", ["iklim", "çevre", "enerji"]),
        ("ulaşım_şehir", ["ulaşım", "şehir", "belediye"]),
        ("dünya_diplomasi", ["dünya", "diplomasi"]),
        ("kültür_sanat", ["kültür", "sanat", "sinema"]),
        ("spor", ["spor", "futbol", "basketbol"]),
        ("adliye_toplum", ["hukuk", "mahkeme", "toplum"]),
        ("siyaset_kamu", ["siyaset", "meclis"]),
        ("afet_güvenlik", ["afet", "deprem", "güvenlik"]),
    ]:
        if any(term in text for term in words):
            tags.extend(words[:2])
            break
    stop = {"türkiyeden", "türkiye", "haberleri", "haber", "son", "dakika", "gündem", "olan", "için", "bugün"}
    for word in re.findall(r"[a-z0-9çğıöşü]{5,}", text):
        if word not in stop:
            tags.append(word)
    unique = []
    for tag in tags:
        tag = tag.strip()[:45]
        if tag and tag.lower() not in {x.lower() for x in unique}:
            unique.append(tag)
        if len(unique) >= 8:
            break
    return unique


def make_viral_hashtags(tags):
    return "#shorts #TürkiyeGündemi"


def upload_to_youtube(video_path, item, publish_at):
    youtube = get_youtube_service()
    title = item.get("title", "").strip()[:90]
    tags = make_viral_tags(item)
    summary = item.get("youtube_description", "").strip()
    description = (
        f"{summary}\n\n"
        f"Kaynak: {item.get('source', item.get('source_name', 'Yayıncı kaynak'))}\n"
        f"Haber bağlantısı: {item.get('url', '')}\n"
        f"Yayın zamanı: {publish_at.isoformat()}\n\n"
        f"{make_viral_hashtags(tags)}"
    )
    body = {
        "snippet": {
            "title": title,
            "description": description[:5000],
            "tags": tags,
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("YouTube yükleme: %s%%", int(status.progress() * 100))
    video_id = response["id"]
    item["youtube_tags"] = tags
    return {
        "video_id": video_id,
        "youtube_url": f"https://youtu.be/{video_id}",
        "publish_at_local": publish_at.isoformat(),
        "publish_at_utc": body["status"]["publishAt"],
        "tags": tags,
        "hashtags": make_viral_hashtags(tags),
    }


'''
    insertion = "\n\n" + block + "\n"
    if 'if __name__ == "__main__":' not in source:
        raise RuntimeError("main.py çalıştırma noktası bulunamadı; içerik yaması uygulanmadı.")
    source = source.replace('if __name__ == "__main__":', insertion + 'if __name__ == "__main__":', 1)

MAIN.write_text(source, encoding="utf-8")
print("Haberdenede geniş gündem kapsamı, konu çeşitliliği ve kanal uyumlu metadata yaması uygulandı")
