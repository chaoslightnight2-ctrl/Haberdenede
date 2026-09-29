"""Confirm YouTube upload receipts and persist each completed video immediately."""
from pathlib import Path

main_file = Path("main.py")
source = main_file.read_text(encoding="utf-8")

replacements = [
    (
        '        "youtube_url": item.get("youtube_url"),\n',
        '        "youtube_url": item.get("youtube_url"),\n'
        '        "video_id": item.get("video_id"),\n'
        '        "upload_status": item.get("upload_status"),\n',
    ),
    (
        '            "youtube_url": upload_info["youtube_url"],\n',
        '            "youtube_url": upload_info["youtube_url"],\n'
        '            "video_id": upload_info["video_id"],\n'
        '            "upload_status": upload_info["upload_status"],\n',
    ),
    (
        '        logger.info("Planlandı: %s -> %s", item["scheduled_slot"], item["title"])\n',
        '        # Save every successful upload before starting the next one.\n'
        '        history = update_history(history, [item])\n'
        '        save_json(PLAN_FILE, {"generated_at": now_tr().isoformat(), "videos": plan_rows})\n'
        '        save_json(HISTORY_FILE, history)\n'
        '        save_json(SELECTED_FILE, {"generated_at": now_tr().isoformat(), "selected_news": selected})\n'
        '        logger.info("Planlandı ve YouTube API yanıtı doğrulandı: %s -> %s (%s)", item["scheduled_slot"], item["title"], upload_info["video_id"])\n',
    ),
    (
        '    save_json(HISTORY_FILE, update_history(history, selected))\n',
        '    save_json(HISTORY_FILE, history)\n',
    ),
]

for old, new in replacements:
    if old not in source:
        raise RuntimeError(f"Güvenilirlik yaması için beklenen kod bulunamadı: {old[:70]!r}")
    source = source.replace(old, new, 1)

anchor = 'if __name__ == "__main__":'
if anchor not in source:
    raise RuntimeError("main.py çalıştırma noktası bulunamadı; güvenilirlik yaması uygulanmadı.")

groq_fix = r'''

# HABERDENEDE_GROQ_JSON_FIX
_groq_last_request_at = None

def _groq_retry_delay_seconds(response, attempt):
    candidates = [
        response.headers.get("Retry-After", ""),
        response.headers.get("x-ratelimit-reset-tokens", ""),
        response.text or "",
    ]
    for value in candidates:
        if not value:
            continue
        try:
            return min(180.0, max(5.0, float(value) + 1.0))
        except (TypeError, ValueError):
            pass
        parts = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*(ms|s|m|h)", str(value).lower())
        if parts:
            seconds = sum(float(amount) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit] for amount, unit in parts)
            if seconds > 0:
                return min(180.0, max(5.0, seconds + 1.0))
    return min(180.0, 65.0 + attempt * 15.0)


def _groq_json_chat(prompt, max_tokens=420, temperature=0.2):
    global _groq_last_request_at
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY GitHub Actions secret'ında yok.")

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    min_interval = 45.0
    for attempt in range(6):
        now = __import__("time").monotonic()
        if _groq_last_request_at is not None:
            wait = max(0.0, min_interval - (now - _groq_last_request_at))
            if wait:
                logger.info("Groq istekleri kota için %.1f saniye aralıkla gönderiliyor", min_interval)
                __import__("time").sleep(wait)
        _groq_last_request_at = __import__("time").monotonic()
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Sen Türkiye’den Haber için kaynak metnine bağlı, dikkatli bir Türkçe haber editörüsün. İstenen alanları içeren tek bir JSON nesnesi döndür."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                # GPT-OSS needs enough completion budget to finish a JSON document.
                "max_completion_tokens": max(2048, int(max_tokens)),
                "reasoning_effort": "low",
                "response_format": {"type": "json_object"},
            },
            timeout=90,
        )
        if response.status_code != 429 or attempt == 5:
            break
        delay = _groq_retry_delay_seconds(response, attempt)
        _groq_last_request_at = __import__("time").monotonic() - min_interval + delay
        logger.warning("Groq 429 sınırı; aynı model %s/6, %.1f saniye bekleyip aynı isteği yeniden deniyor", attempt + 1, delay)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        details = re.sub(r"\s+", " ", response.text or "")[:500]
        raise RuntimeError(f"Groq isteği başarısız: HTTP {response.status_code}, model={model}, yanıt={details}") from exc

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"Groq boş choices döndürdü; model={model}.")
    content = choices[0].get("message", {}).get("content", "")
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise RuntimeError(f"Groq geçerli JSON nesnesi döndürmedi; model={model}.")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Groq JSON yanıtı nesne değil; model={model}.")
    logger.info("Groq JSON yanıtı doğrulandı: model=%s", model)
    return content


def make_viral_tags(item):
    bucket = item.get("topic_bucket") or detect_topic_bucket(item)
    topic_tags = {
        "bilim_teknoloji": ["teknoloji haberleri", "bilim haberleri"],
        "ekonomi_yasam": ["ekonomi haberleri", "tüketici haberleri"],
        "sağlık_eğitim": ["sağlık haberleri", "eğitim haberleri"],
        "iklim_enerji": ["iklim haberleri", "enerji haberleri"],
        "ulaşım_şehir": ["ulaşım haberleri", "şehir haberleri"],
        "dünya_diplomasi": ["dünya haberleri", "dış politika"],
        "kültür_sanat": ["kültür sanat", "kültür haberleri"],
        "spor": ["spor haberleri", "Türkiye spor"],
        "adliye_toplum": ["hukuk haberleri", "toplum haberleri"],
        "siyaset_kamu": ["Türkiye siyaseti", "kamu politikası"],
        "afet_güvenlik": ["afet haberleri", "güvenlik haberleri"],
        "gündem_genel": ["Türkiye gündemi", "Türkiye haberleri"],
    }
    tags = ["Türkiye'den Haber", "Türkiye gündemi"] + topic_tags.get(bucket, topic_tags["gündem_genel"])
    stop = {
        "türkiye", "haber", "haberleri", "gündem", "son", "dakika", "bugün", "olan", "için",
        "hakkında", "açıklama", "açıklaması", "yeni", "önemli", "dikkat", "sonrası", "öncesi",
        "karşı", "göre", "dedi", "oldu", "ile", "bir", "daha", "nasıl", "neden",
    }
    words = re.findall(r"[a-z0-9çğıöşü]{4,}", normalize_text(item.get("title", "")))
    tags.extend(word for word in words if word not in stop)
    unique = []
    seen = set()
    for tag in tags:
        clean = re.sub(r"\s+", " ", tag.strip())[:45]
        if clean and clean.casefold() not in seen:
            unique.append(clean)
            seen.add(clean.casefold())
        if len(unique) == 10:
            break
    return unique


def make_viral_hashtags(tags, item=None):
    bucket = detect_topic_bucket(item or {})
    topic_hashtags = {
        "bilim_teknoloji": "#Teknoloji", "ekonomi_yasam": "#Ekonomi",
        "sağlık_eğitim": "#Sağlık", "iklim_enerji": "#Çevre",
        "ulaşım_şehir": "#ŞehirYaşamı", "dünya_diplomasi": "#DünyaHaberleri",
        "kültür_sanat": "#KültürSanat", "spor": "#Spor",
        "adliye_toplum": "#Hukuk", "siyaset_kamu": "#TürkiyeSiyaseti",
        "afet_güvenlik": "#Gündem", "gündem_genel": "#TürkiyeGündemi",
    }
    specific = topic_hashtags.get(bucket, "#TürkiyeGündemi")
    return f"#Shorts {specific} #TürkiyeGündemi"


_youtube_upload_before_receipt_check = upload_to_youtube


def upload_to_youtube(video_path, item, publish_at):
    result = _youtube_upload_before_receipt_check(video_path, item, publish_at)
    video_id = result.get("video_id")
    if not video_id:
        raise RuntimeError("YouTube API yanıtında video ID yok; yükleme onaylanmadı.")
    result["upload_status"] = "api_insert_confirmed"
    item["upload_status"] = result["upload_status"]
    logger.info("YouTube yükleme onayı: video_id=%s; videos.insert başarılı.", video_id)
    return result
'''

source = source.replace(anchor, groq_fix + "\n\n" + anchor, 1)
main_file.write_text(source, encoding="utf-8")
print("Groq JSON settings and per-upload confirmation patch applied")

