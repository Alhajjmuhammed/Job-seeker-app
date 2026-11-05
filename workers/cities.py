"""
City names as workers and clients type them, reduced to one key per place,
so "ZANZIBAR", "Zanzibra", "Stone Town" and "Fuoni" all match "Zanzibar"
when a request is matched to workers by city.
"""
import re

# neighbourhood / spelling -> place
_ALIASES = {
    'zanzibar': ['zanzibar', 'zanzibra', 'zanziber', 'zanzbar', 'znz', 'unguja', 'stonetown',
                 'stone town', 'mji mkongwe', 'mjini', 'mjini magharibi', 'fuoni', 'mbweni',
                 'mwanakwerekwe', 'amani', 'kiembe samaki', 'chukwani', 'tunguu', 'bububu',
                 'mombasa zanzibar', 'darajani', 'michenzani', 'kwahani', 'jang ombe', 'jangombe',
                 'magomeni zanzibar', 'kilimani zanzibar', 'mtoni', 'kibweni', 'fumba', 'paje',
                 'nungwi', 'kizimkazi', 'chwaka', 'makunduchi'],
    'pemba': ['pemba', 'chake chake', 'chakechake', 'wete', 'mkoani'],
    'dar es salaam': ['dar es salaam', 'dar es salam', 'daressalaam', 'dar', 'dsm', 'dar-es-salaam',
                      'kinondoni', 'ilala', 'temeke', 'ubungo', 'kigamboni', 'mikocheni', 'sinza',
                      'mbezi', 'kariakoo', 'masaki', 'upanga', 'tegeta', 'kimara'],
    'dodoma': ['dodoma'],
    'arusha': ['arusha'],
    'mwanza': ['mwanza'],
    'mbeya': ['mbeya'],
    'morogoro': ['morogoro'],
    'tanga': ['tanga'],
    'moshi': ['moshi', 'kilimanjaro'],
}
_LOOKUP = {alias: place for place, aliases in _ALIASES.items() for alias in aliases}


def city_key(name):
    """One comparable key for a typed city name ('' when empty)."""
    text = re.sub(r'[^a-z ]+', ' ', (name or '').lower())
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ''
    if text in _LOOKUP:
        return _LOOKUP[text]
    # "Fuoni, Zanzibar" / "Mbweni Unguja": any known word inside
    for alias, place in sorted(_LOOKUP.items(), key=lambda item: -len(item[0])):
        if re.search(rf'\b{re.escape(alias)}\b', text):
            return place
    return text
