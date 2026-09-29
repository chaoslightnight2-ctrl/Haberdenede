"""Fail fast unless the configured Groq model returns valid JSON."""
import json
import os
import re
import sys

import requests


def main() -> None:
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
                {"role": "system", "content": "Return only the requested JSON object."},
                {"role": "user", "content": 'Return exactly this JSON object: {"ok":true}'},
            ],
            "temperature": 0,
            "max_completion_tokens": 2048,
            "reasoning_effort": "low",
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        details = re.sub(r"\s+", " ", response.text or "")[:500]
        raise RuntimeError(f"Groq sağlık kontrolü başarısız: HTTP {response.status_code}, model={model}, yanıt={details}") from exc

    payload = response.json()
    choices = payload.get("choices") or []
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    match = re.search(r"\{[\s\S]*\}", content)
    if not match or json.loads(match.group(0)).get("ok") is not True:
        raise RuntimeError(f"Groq sağlık kontrolü geçersiz JSON aldı; model={model}.")
    print(f"Groq hazır: model={model}; JSON yanıtı doğrulandı.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        sys.exit(1)

