def _normalize_full_width_to_half_width(text):
    """
    Converts full-width digits and periods in a string to half-width.
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
    
    return text