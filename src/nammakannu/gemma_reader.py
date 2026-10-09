
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemma-4-26b-a4b-it"

PROMPT = """
You are NammaKannu, a Bengaluru BMTC bus-board assistant.

Analyze the provided bus photo. Read visible Kannada and English text.
Extract only information supported by the image.

Return valid JSON with these fields:
{
  "is_bus_board": true,
  "route_number": null,
  "destination": null,
  "visible_text": [],
  "language": [],
  "confidence": "low"
}

Rules:
- route_number: the clearly visible BMTC route number, otherwise null.
- destination: the destination or direction shown, otherwise null.
- visible_text: short list of readable words from the board.
- language: languages actually detected, such as Kannada or English.
- confidence: high, medium, or low.
- Do not invent missing text or route numbers.
- Return JSON only, without Markdown fences.
"""


def read_bus_board(image_bytes: bytes, mime_type: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            ),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
        ),
    )

    text = (response.text or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    result = json.loads(text)

    if not isinstance(result, dict):
        raise ValueError("Gemma returned an unexpected response.")

    return result
