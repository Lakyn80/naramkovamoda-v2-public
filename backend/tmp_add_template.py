# -*- coding: utf-8 -*-
from app.modules.ai.rag.chroma_client import add_document
from app.modules.ai.rag.embeddings import embed_text

text = (
"💚 Náramek na nohu Lesní energie – příroda, svěžest a síla 🍀 O: 22 cm\n\n"
"Lehký a hravý náramek inspirovaný zelení lesa a energií přírody. "
"Kombinace lávových kamenů, černých a zeleno-žlutých korálků přináší "
"rovnováhu, vitalitu a radost z pohybu.\n"
"Ideální doplněk pro letní dny, bosé procházky v trávě nebo dovolenou u vody – "
"symbol svobody a propojení se zemí.\n\n"
"✨ Popis produktu:\n"
"– ručně vyráběný náramek na nohu\n"
"– materiál: lávové kameny, skleněné korálky, zeleno-žluté minerální korálky\n"
"– barvy: černá, zelená, žlutá\n"
"– pružný provázek, univerzální velikost\n\n"
"💎 Styl: přírodní, letní, energický"
)

embedding = embed_text(text)

add_document(
    doc_id="template_bracelet_250",
    text=text,
    embedding=embedding,
    metadata={"product_type": "bracelet"}
)

print("ULOŽENO DO CHROMA jako šablona pro bracelet (ID: template_bracelet_250)")
