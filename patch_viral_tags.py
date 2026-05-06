from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

upload_start = s.index("def upload_to_youtube(")
build_start = s.index("\ndef build_video_for_item(", upload_start)

new_block = r'''def make_viral_tags(item: dict[str, Any]) -> list[str]:
    text = normalize_text(item.get("title", "") + " " + item.get("summary", ""))
    tags = [
        "shorts",
        "haber",
        "son dakika",
        "gündem",
        "türkiye",
        "turkey news",
        "breaking news",
        "youtube shorts",
        "viral haber",
        "gündem haberleri",
    ]

    topic_tags = {
        "deprem": ["deprem", "afad", "kandilli", "son deprem"],
        "yangın": ["yangın", "afet", "itfaiye", "son dakika yangın"],
        "sel": ["sel", "afet", "sağanak", "son dakika sel"],
        "kaza": ["kaza", "trafik kazası", "son dakika kaza"],
        "ekonomi": ["ekonomi", "para", "piyasa", "ekonomi haberleri"],
        "enflasyon": ["enflasyon", "zam", "ekonomi", "hayat pahalılığı"],
        "faiz": ["faiz", "merkez bankası", "ekonomi", "piyasa"],
        "dolar": ["dolar", "kur", "ekonomi", "piyasa"],
        "borsa": ["borsa", "borsa istanbul", "piyasa", "ekonomi"],
        "meclis": ["meclis", "siyaset", "ankara", "politika"],
        "bakan": ["bakan", "siyaset", "ankara", "açıklama"],
        "cumhurbaşkan": ["cumhurbaşkanı", "erdoğan", "siyaset", "ankara"],
        "erdoğan": ["erdoğan", "cumhurbaşkanı", "siyaset", "son dakika"],
        "seçim": ["seçim", "siyaset", "oy", "politika"],
        "operasyon": ["operasyon", "polis", "gözaltı", "adliye"],
        "gözaltı": ["gözaltı", "polis", "adliye", "son dakika"],
        "tutuk": ["tutuklama", "mahkeme", "adliye", "son dakika"],
        "mahkeme": ["mahkeme", "adliye", "dava", "karar"],
        "spor": ["spor", "futbol", "maç", "spor haberleri"],
        "transfer": ["transfer", "futbol", "spor", "transfer haberleri"],
        "derbi": ["derbi", "futbol", "spor", "maç"],
        "sosyal medya": ["sosyal medya", "viral", "gündem", "trend"],
    }

    for key, values in topic_tags.items():
        if key in text:
            tags.extend(values)

    for city in ["istanbul", "ankara", "izmir", "muğla", "antalya", "bursa", "adana", "konya", "trabzon", "diyarbakır"]:
        if city in text:
            tags.append(city)
            tags.append(f"{city} haber")

    # Başlıktan güçlü kelimeleri de etiket olarak ekle.
    words = [w for w in text.split() if len(w) >= 5]
    stop = {"haber", "son", "dakika", "türkiye", "bugün", "oldu", "olan", "için", "sonrası", "öncesi", "listesi"}
    for word in words:
        if word not in stop:
            tags.append(word)

    clean_tags = []
    seen = set()
    for tag in tags:
        tag = re.sub(r"\s+", " ", tag.strip().lower())
        tag = tag[:45]
        if not tag or tag in seen:
            continue
        seen.add(tag)
        clean_tags.append(tag)
        if len(clean_tags) >= 28:
            break
    return clean_tags


def make_viral_hashtags(tags: list[str]) -> str:
    base = ["shorts", "haber", "sondakika", "gündem", "türkiye", "viral"]
    extra = []
    for tag in tags:
        compact = re.sub(r"[^A-Za-z0-9çğıöşüÇĞİÖŞÜ]", "", tag)
        if compact and compact.lower() not in {x.lower() for x in base}:
            extra.append(compact)
        if len(extra) >= 6:
            break
    hashtags = base + extra
    return " ".join("#" + h for h in hashtags[:12])


def upload_to_youtube(video_path: Path, item: dict[str, Any], publish_at: datetime) -> dict[str, Any]:
    youtube = get_youtube_service()
    title = item["title"].strip()
    if "#shorts" not in title.lower():
        title = f"{title} #shorts"

    viral_tags = make_viral_tags(item)
    viral_hashtags = make_viral_hashtags(viral_tags)

    description = (
        f"{item['script']}\n\n"
        f"Kaynak link: {item['url']}\n"
        f"Kaynak: {item.get('source', 'Google News RSS')}\n"
        f"Yayın zamanı: {publish_at.isoformat()}\n\n"
        f"{viral_hashtags}"
    )
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": viral_tags,
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
    item["youtube_tags"] = viral_tags
    item["youtube_hashtags"] = viral_hashtags
    return {
        "video_id": video_id,
        "youtube_url": f"https://youtu.be/{video_id}",
        "publish_at_local": publish_at.isoformat(),
        "publish_at_utc": body["status"]["publishAt"],
        "tags": viral_tags,
        "hashtags": viral_hashtags,
    }

'''

s = s[:upload_start] + new_block + s[build_start + 1:]

# video_plan içine de etiketleri yaz.
s = s.replace('"youtube_url": upload_info["youtube_url"],', '"youtube_url": upload_info["youtube_url"],\n            "tags": upload_info.get("tags", []),\n            "hashtags": upload_info.get("hashtags", ""),')

p.write_text(s, encoding="utf-8")
print("Viral tags patch applied")
