import asyncio
import random
from typing import List

# Mock AI tagging service
# In a real app, you would use a model like CLIP, MobileNet, or an external API.

SCENE_TAGS = ["Nature", "Urban", "Interior", "Portrait", "Landscape", "Action", "Night"]
OBJECT_TAGS = ["Tree", "Beach", "Dog", "Cat", "Car", "Bicycle", "Food", "Sunset", "Mountain", "Flower"]
VIBE_TAGS = ["Cozy", "Bright", "Moody", "Energetic", "Vintage", "Peaceful"]

async def suggest_tags(media_id: str, title: str, caption: str) -> List[str]:
    """Simulates AI analyzing the image/video to suggest tags."""
    await asyncio.sleep(2)  # Simulate processing time
    
    tags = set()
    
    # Simple keyword matching from title/caption
    text = f"{title or ''} {caption or ''}".lower()
    
    keywords = {
        "beach": ["Beach", "Ocean", "Summer"],
        "dog": ["Dog", "Pet", "Animal"],
        "cat": ["Cat", "Pet", "Animal"],
        "forest": ["Nature", "Tree", "Forest"],
        "mountain": ["Nature", "Mountain", "Landscape"],
        "sunset": ["Sunset", "Sky", "Vibrant"],
        "food": ["Food", "Interior"],
        "city": ["Urban", "City", "Street"],
        "baby": ["Portrait", "Family", "Candid"],
        "birthday": ["Celebration", "Party", "Interior"],
    }
    
    for word, suggested in keywords.items():
        if word in text:
            tags.update(suggested)
            
    # Randomly add some "detected" tags if nothing found to make it look active
    if not tags:
        tags.add(random.choice(SCENE_TAGS))
        if random.random() > 0.5:
            tags.add(random.choice(OBJECT_TAGS))
        if random.random() > 0.7:
            tags.add(random.choice(VIBE_TAGS))
            
    return list(tags)
