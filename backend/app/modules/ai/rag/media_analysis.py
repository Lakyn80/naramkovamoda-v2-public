from typing import List, Union

from .models.media import MediaAsset
from .vision_client import analyze_image_with_vision, normalize_tags


def analyze_media_for_session(
    session_id: Union[int, str],
    media_assets: List[MediaAsset],
) -> List[MediaAsset]:
    """
    KOSTRA PIPELINE – zatím bez DB.

    Co tato funkce dělá:
    1) projde všechny MediaAsset dané session
    2) zavolá Google Vision (zatím mock)
    3) uloží vision_json + tags zpět do MediaAsset
    4) vrátí aktualizované MediaAsset

    POZDĚJI:
    - místo parametru media_assets je budeme načítat z DB podle session_id
    - a po úpravě je opět uložíme do DB
    """

    updated_assets = []

    for asset in media_assets:
        # Použijeme původní obrázek (nebo webp, pokud už existuje)
        image_path = asset.path_webp or asset.path_original

        # Zavoláme Vision
        vision_result = analyze_image_with_vision(image_path)

        # Normalizujeme tagy
        tags = normalize_tags(vision_result)

        # Uložíme zpět do modelu
        asset.vision_json = vision_result
        asset.tags = tags

        updated_assets.append(asset)

    return updated_assets
