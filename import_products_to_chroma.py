import json
from app.modules.ai.rag.chroma_client import add_document
from app.modules.ai.rag.embeddings import embed_text

with open("all_products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

count = 0

for p in products:
    pid = p.get("id")
    name = p.get("name") or ""
    description = p.get("description") or ""

    text = f"{name}\n\n{description}".strip()
    if not text:
        continue

    doc_id = f"product_{pid}"
    embedding = embed_text(text)

    add_document(
        doc_id=doc_id,
        text=text,
        embedding=embedding,
        metadata={"source": "product", "product_id": pid},
    )

    count += 1

print(f"Imported {count} products into ChromaDB as RAG documents.")
