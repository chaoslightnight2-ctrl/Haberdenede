"""Add a human-ready external sharing pack to each Haberdenede run."""
from pathlib import Path

MAIN = Path("main.py")
source = MAIN.read_text(encoding="utf-8")
marker = "# HABERDENEDE_EXTERNAL_DISTRIBUTION_PACK"

if marker not in source:
    block = r'''
# HABERDENEDE_EXTERNAL_DISTRIBUTION_PACK
def write_external_distribution_pack(plan_rows):
    """Create platform-specific copy; never posts to external accounts."""
    lines = [
        "# Haber Denede — Dış paylaşım paketi",
        "",
        "> Video YouTube'da herkese açık olduktan sonra paylaşın. Zamanlanmış video, yayın saatinden önce izlenemez.",
        "> Instagram/TikTok için MP4'ü yerel video olarak yükleyin; YouTube bağlantısını profil bağlantısına ekleyin.",
        "",
    ]
    for row in plan_rows:
        title = str(row.get("title", "")).strip()
        link = str(row.get("youtube_url", "")).strip()
        hook = str(row.get("hook", "")).strip() or title
        description = str(row.get("description", "")).strip()
        slot = str(row.get("publish_at_local", "")).strip()
        media = str(row.get("media_path", "")).strip()
        teaser = description[:220].strip()
        lines.extend([
            f"## {title}",
            "",
            f"- Yayına alınacağı saat (Türkiye): {slot}",
            f"- YouTube: {link}",
            f"- Yeniden yüklemek için MP4: {media}",
            "",
            "### X / Threads / Facebook",
            "",
            f"{hook}",
            f"{link}",
            "",
            "### WhatsApp / Telegram",
            "",
            f"{title}",
            f"{teaser}",
            f"Videoyu izle: {link}",
            "",
            "### Instagram Reels / TikTok",
            "",
            f"{hook}",
            "Gündemin devamı Türkiye’den Haber YouTube kanalında. YouTube bağlantısını profil bağlantısına ekleyin.",
            "#TürkiyeGündemi #Haber",
            "",
            "---",
            "",
        ])
    Path("distribution_pack.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


'''
    anchor = 'if __name__ == "__main__":'
    if anchor not in source:
        raise RuntimeError("main.py çalıştırma noktası bulunamadı; dış dağıtım paketi uygulanmadı.")
    source = source.replace(anchor, block + anchor, 1)

save_anchor = 'save_json(PLAN_FILE, {"generated_at": now_tr().isoformat(), "videos": plan_rows})'
call = save_anchor + '\n    write_external_distribution_pack(plan_rows)'
if "write_external_distribution_pack(plan_rows)" not in source:
    if save_anchor not in source:
        raise RuntimeError("video_plan kaydetme satırı bulunamadı; dış dağıtım paketi uygulanmadı.")
    source = source.replace(save_anchor, call, 1)

source = source.replace(
    '"youtube_url": upload_info["youtube_url"],',
    '"youtube_url": upload_info["youtube_url"],\n            "hook": item.get("shorts_hook", ""),\n            "description": item.get("youtube_description", ""),\n            "media_path": f"generated_videos/short_{index}.mp4",',
    1,
)
MAIN.write_text(source, encoding="utf-8")
print("Dış paylaşım kopyaları distribution_pack.md dosyasına eklendi")
