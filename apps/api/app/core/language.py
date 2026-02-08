def detect_language(text: str) -> str:
    """
    Returns:
      "am" if Ethiopic script is detected
      "en" otherwise
    """
    for ch in text:
        o = ord(ch)
        if 0x1200 <= o <= 0x139F:  # Ethiopic block + extensions
            return "am"
    return "en"
