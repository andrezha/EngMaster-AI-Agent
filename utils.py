import re
def _normalize_full_width_to_half_width(text):
    """
    Converts full-width digits, periods, letters, and spaces in a string to half-width.
    Ensures a string is always returned, even if input is None.
    """
    if text is None:
        return ""

    text = str(text) # Ensure it's a string before processing
    
    # Mapping for full-width digits to half-width
    full_to_half_digits = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    
    # Replace full-width digits
    for full, half in full_to_half_digits.items():
        text = text.replace(full, half)
    
    # Replace full-width period
    text = text.replace('．', '.')
    # Replace full-width brackets
    text = text.replace('【', '[')
    text = text.replace('】', ']')
    # Replace full-width parentheses
    text = text.replace('（', '(')
    text = text.replace('）', ')')
    
    # Mapping for full-width English letters to half-width
    full_to_half_letters = {
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
        'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
        'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
        'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y',
        'Ｚ': 'Z',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y',
        'ｚ': 'z'
    }
    for full, half in full_to_half_letters.items():
        text = text.replace(full, half)

    # Replace full-width space
    text = text.replace('　', ' ')
    
    return text