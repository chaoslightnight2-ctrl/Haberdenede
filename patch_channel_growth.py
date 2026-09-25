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
source = source.replace('"llama-3.3-70b-versatile"', '"openai/gpt-oss-120b"')

# Preserve the editorial inputs beside each upload so topic-level results can be compared later.
plan_anchor = '"viral_score": item["viral_score"],'
plan_fields = '''"viral_score": item["viral_score"],
            "topic_bucket": item.get("topic_bucket", "gündem_genel"),
            "source_headline": item.get("source_headline", ""),
            "narration": item.get("script", ""),
            "description": item.get("youtube_description", ""),'''
if plan_anchor in source:
    source = source.replace(plan_anchor, plan_fields, 1)

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


def _groq_json_chat(prompt, max_tokens=420, temperature=0.2):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY GitHub Actions secret'ında yok.")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Sen Türkiye'den Haber kanalı için kaynaklara bağlı, dikkatli bir Türkçe haber editörüsün."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        details = re.sub(r"\s+", " ", response.text or "")[:600]
        raise RuntimeError(
            f"Groq isteği başarısız: HTTP {response.status_code}, model={model}, yanıt={details}"
        ) from exc
    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"Groq boş choices döndürdü; model={model}.")
    return choices[0].get("message", {}).get("content", "")


def generate_news_script(item):
    source_title = clean_news_title_for_script(item.get("title", ""))
    content = get_best_news_content_for_script(item)
    if not content:
        raise RuntimeError(f"Doğrulanabilir haber metni yetersiz; Groq'a gönderilmedi: {source_title}")
    topic = detect_topic_bucket(item)
    angle_guidance = {
        "ekonomi_yasam": "Önce değişen fiyatı, kuralı veya kararı ve açıkça belirtilen etkilenen grubu anlat.",
        "sağlık_eğitim": "Önce kararın ya da gelişmenin hangi hasta, öğrenci veya kurumu ilgilendirdiğini söyle.",
        "bilim_teknoloji": "Önce keşif/ürün/güvenlik gelişmesinin ne olduğunu ve kaynakta belirtilen kullanım etkisini açıkla.",
        "iklim_enerji": "Önce yer, olay ve doğrulanmış ölçü/değişikliği aktar; tehlike abartısı ekleme.",
        "ulaşım_şehir": "Önce hangi yerde hangi hat, yol veya hizmetin nasıl değiştiğini söyle.",
        "dünya_diplomasi": "Önce tarafları ve alınan kararı/sonraki adımı açıkla; taraf tutan dil kullanma.",
        "kültür_sanat": "Önce eser, etkinlik ya da kişiyle ilgili somut yeniliği ve tarihi/yer bilgisini ver.",
        "spor": "Önce takım/sporcu ve maçın/kararın sonucunu, kaynakta varsa skorla söyle.",
        "adliye_toplum": "Önce yargı aşamasını ve ilgili kişilerin statüsünü doğru aktar; iddiayı hüküm gibi sunma.",
        "siyaset_kamu": "Önce karar/açıklama ve kimleri ilgilendirdiğini, kaynakta açıklandığı kadarıyla anlat.",
        "afet_güvenlik": "Önce teyit edilmiş yer, olay ve resmi durum bilgisini ver; doğrulanmamış sayı kullanma.",
        "gündem_genel": "Önce en yeni somut gelişmeyi ve kaynakta belirtilen doğrudan etkisini aktar.",
    }.get(topic, "Önce en yeni somut gelişmeyi aktar.")
    prompt = f"""
Türkiye’den Haber adlı geniş kapsamlı haber kanalı için kısa video metadatası ve anlatımı üret.
Açılışta selam, kanal tanıtımı, soru, “şok/olay” gibi boş merak kancası kullanma; ilk cümlede somut gelişmeyi
ve haberin ana kişisini/kurumunu söyle. Başlığın vaat ettiği bilgiyi açılışta hemen ver.
Yalnızca başlık ve kaynak metninde açıkça bulunan olguları kullan. İddiaları iddia olarak belirt; kesinleşmemiş
bilgiyi kesin hüküm gibi yazma. Kaynakta olmayan neden, sonuç, sayı, tarih veya yorum ekleme.
Kategoriye uygun anlatım yönü: {angle_guidance}
Anlatım 35-60 Türkçe kelime, tek paragraf ve doğal seslendirmeye uygun olsun. Her cümle yeni bir bilgi taşısın;
tekrar, dolgu, genel takip/abone çağrısı ve yapay cliffhanger ekleme.
Başlık doğru, özgün ve en fazla 70 karakter olsun; en önemli kişi/konu başta yer alsın. #shorts, ALL CAPS ve
yanıltıcı kesinlik kullanma. Açıklama her haber için farklı, ilk cümlesi haberi doğrudan özetleyen 1-2 cümle olsun;
ana kişi/konu terimlerinden 1-2 tanesini doğal biçimde içersin. Hashtag veya etiket listesi yazma.
Geçerli JSON dışında hiçbir şey döndürme:
{{"title":"...","narration":"...","description":"..."}}

Kanal kapsamı/kategori: {topic}
Kaynak başlığı: {source_title}
Haber metni: {content[:4200]}
"""
    try:
        raw = _groq_json_chat(prompt, max_tokens=480, temperature=0.2)
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("Groq JSON nesnesi döndürmedi.")
        data = json.loads(match.group(0))
        new_title = clean_generated_text(str(data.get("title", ""))).strip(" .-|:")
        narration = clean_generated_text(str(data.get("narration", ""))).strip()
        description = clean_generated_text(str(data.get("description", ""))).strip()
        if not new_title or not narration or not description:
            raise ValueError("Groq title, narration veya description alanını boş bıraktı.")
        if len(new_title) > 70 or not 35 <= len(narration.split()) <= 65:
            raise ValueError("Groq çıktısı uzunluk denetimini geçemedi.")
    except Exception as exc:
        logger.error("Groq üretimi başarısız; yedek anlatıma geçilmeden çalışma durduruluyor: %s", exc)
        raise

    item["source_headline"] = item.get("title", "")
    item["youtube_description"] = description
    item["title"] = new_title
    resolved = item.get("resolved_url", "")
    if resolved.startswith("https://") and "news.google.com" not in resolved:
        item["url"] = resolved
    logger.info("Groq (%s) ile kanal uyumlu başlık ve anlatım üretildi: %s", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), new_title)
    return narration


def build_background_queries(item):
    topic = detect_topic_bucket(item)
    topic_queries = {
        "bilim_teknoloji": ["technology lab innovation", "data center servers", "scientist laboratory", "satellite earth"],
        "ekonomi_yasam": ["grocery shopping market prices", "small business shop", "financial district street", "house construction city"],
        "sağlık_eğitim": ["doctor hospital hallway", "medical research laboratory", "students classroom university", "school campus"],
        "iklim_enerji": ["wind turbines renewable energy", "solar panels power", "drought dry lake", "forest conservation"],
        "ulaşım_şehir": ["city public transport metro", "train station commute", "urban traffic aerial", "city infrastructure construction"],
        "dünya_diplomasi": ["international diplomacy flags", "world city skyline", "united nations building", "global shipping port"],
        "kültür_sanat": ["museum art gallery", "cinema audience screen", "live music concert stage", "library books"],
        "spor": ["football stadium action", "basketball game arena", "volleyball match court", "sports training athlete"],
        "adliye_toplum": ["courthouse exterior", "justice scales legal documents", "community city people"],
        "siyaset_kamu": ["parliament building exterior", "government press briefing", "city hall public meeting"],
        "afet_güvenlik": ["emergency responders training", "storm weather city", "firefighters emergency response", "earthquake preparedness"],
        "gündem_genel": ["turkey city street news", "people watching news television", "urban life Istanbul"],
    }
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    queries = list(topic_queries.get(topic, topic_queries["gündem_genel"]))
    for key, mapped in BACKGROUND_HINTS.items():
        if key in text:
            queries.extend(mapped)
    stop = {"turkiye", "haber", "haberleri", "gundem", "son", "dakika", "bugun", "aciklama", "karar", "oldu"}
    title_words = [word for word in normalize_text(item.get("title", "")).split() if len(word) >= 4 and word not in stop]
    if len(title_words) >= 2:
        queries.append(f"{title_words[0]} {title_words[1]} news context")
    queries.extend(["news studio background", "city aerial turkey"])
    return list(dict.fromkeys(queries))


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
