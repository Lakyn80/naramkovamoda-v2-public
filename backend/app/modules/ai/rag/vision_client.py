# -*- coding: utf-8 -*-
from typing import Dict, List, Any
import os
import re

from google.cloud import vision


def analyze_image_with_vision(image_path: str) -> Dict[str, Any]:
    """
    Analýza obrázku pomocí Google Vision API.
    Čte data z label_annotations, localized_object_annotations, web_entities a text_annotations.
    Vrátí slovník: labels, scores, objects, web_entities, text.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Soubor nenalezen: {image_path}")

    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    label_resp = client.label_detection(image=image)
    object_resp = client.object_localization(image=image)
    web_resp = client.web_detection(image=image)
    text_resp = client.text_detection(image=image)

    labels: List[str] = []
    scores: List[float] = []
    for ann in label_resp.label_annotations:
        labels.append(ann.description.lower() if ann.description else "")
        scores.append(float(ann.score) if ann.score is not None else 0.0)

    objects: List[str] = []
    for obj in object_resp.localized_object_annotations:
        if obj.name:
            objects.append(obj.name.lower())

    web_entities: List[str] = []
    if web_resp.web_detection and web_resp.web_detection.web_entities:
        for ent in web_resp.web_detection.web_entities:
            if ent.description:
                web_entities.append(ent.description.lower())

    text = ""
    if text_resp.text_annotations:
        text = text_resp.text_annotations[0].description or ""

    return {
        "labels": labels,
        "scores": scores,
        "objects": objects,
        "web_entities": web_entities,
        "text": text,
    }


def normalize_tags(vision_result: Dict[str, Any], deduplicate: bool = False) -> List[str]:
    """
    Z Vision výsledku vybere labely/objekty/web entity a vrátí je jako seznam
    normalizovaných řetězců (strip, lower).
    Volitelně může odstranit duplicity.
    """
    labels = vision_result.get("labels", [])
    objects = vision_result.get("objects", [])
    web_entities = vision_result.get("web_entities", [])
    text = vision_result.get("text", "")

    base = [str(t).strip().lower() for t in [*labels, *objects, *web_entities] if t]

    size_tags: List[str] = []
    if text:
        for match in re.finditer(r"\b(\d+(?:[.,]\d+)?)\s*(mm|cm)\b", text, flags=re.I):
            val = match.group(1).replace(",", ".")
            unit = match.group(2).lower()
            size_tags.append(f"rozměr {val} {unit}")

    merged = [*base, *size_tags]
    if deduplicate:
        return list(dict.fromkeys(merged))
    return merged
