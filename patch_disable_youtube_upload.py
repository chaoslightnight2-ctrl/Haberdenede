from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

start = s.index("def upload_to_youtube(")
end = s.index("\ndef build_video_for_item(", start)

replacement = r'''def upload_to_youtube(video_path: Path, item: dict[str, Any], publish_at: datetime) -> dict[str, Any]:
    """YouTube upload temporarily disabled.

    Video is rendered locally and later uploaded as a GitHub Actions artifact.
    """
    logger.info("YouTube yükleme kapalı. Video lokal artifact olarak saklanacak: %s", video_path)
    viral_tags = make_viral_tags(item) if "make_viral_tags" in globals() else ["shorts", "haber", "gündem", "türkiye"]
    viral_hashtags = make_viral_hashtags(viral_tags) if "make_viral_hashtags" in globals() else "#shorts #haber #gündem #türkiye"
    item["youtube_tags"] = viral_tags
    item["youtube_hashtags"] = viral_hashtags
    return {
        "video_id": None,
        "youtube_url": None,
        "publish_at_local": publish_at.isoformat(),
        "publish_at_utc": publish_at.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "video_path": str(video_path),
        "upload_disabled": True,
        "tags": viral_tags,
        "hashtags": viral_hashtags,
    }

'''

s = s[:start] + replacement + s[end + 1:]
p.write_text(s, encoding="utf-8")
print("YouTube upload disabled; local artifact mode enabled")
