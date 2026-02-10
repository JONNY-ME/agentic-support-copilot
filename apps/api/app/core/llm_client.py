import os
from openai import OpenAI

def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )

def generate_answer(prompt: str) -> str:
    client = get_client()
    model = os.getenv("CHAT_MODEL", "gemini-3-flash-preview")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""

def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_client()
    model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]
