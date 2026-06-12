import bleach

def sanitize_text(text: str) -> str:
    """
    Strips all HTML tags from the input string to prevent XSS.
    """
    if not text:
        return text
    # Strip all tags and attributes
    return bleach.clean(text, tags=[], attributes={}, strip=True)
