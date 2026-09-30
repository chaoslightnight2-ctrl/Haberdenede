"""Check the configured Groq model with the production quota/retry rules."""
import logging
import os
import sys

from groq_client import chat_json, object_schema


def main() -> None:
    result = chat_json(
        'Return one JSON object with ok set to true',
        temperature=0,
        max_tokens=512,
        schema=object_schema({'ok': {'type': 'boolean'}}),
    )
    if result.get('ok') is not True:
        raise RuntimeError('Groq model healthcheck did not return ok=true')
    print(f"Groq ready: model={os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')}; JSON response verified")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        sys.exit(1)
