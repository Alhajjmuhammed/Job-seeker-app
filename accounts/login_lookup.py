"""
Log in with an email, a username or a phone number - whichever the user
remembers. Shared by the website and the app so both accept the same thing.
"""

import re

from django.contrib.auth import authenticate
from django.db.models import Q

from .models import User

AMBIGUOUS = 'ambiguous'


def _phone_tail(value):
    """Last 9 digits: 0712 345 678, +255712345678, 255712345678 and 712345678
    are all the same Tanzanian number."""
    digits = re.sub(r'\D', '', value or '')
    return digits[-9:] if len(digits) >= 9 else None


def find_login_candidates(identifier):
    identifier = (identifier or '').strip()
    if not identifier:
        return []

    if '@' in identifier:
        found = User.objects.filter(email__iexact=identifier)
        if not found.exists():
            # usernames may contain @ too
            found = User.objects.filter(username__iexact=identifier)
        return list(found)

    users = list(User.objects.filter(username__iexact=identifier))
    tail = _phone_tail(identifier)
    if tail and re.fullmatch(r'[\d\s+()-]+', identifier):
        seen = {u.pk for u in users}
        for u in User.objects.filter(Q(phone_number__endswith=tail[-4:]) & ~Q(phone_number='')):
            if u.pk not in seen and _phone_tail(u.phone_number) == tail:
                users.append(u)
    return users


def authenticate_identifier(request, identifier, password):
    """
    Returns the user, None for wrong details, or AMBIGUOUS when the password
    fits more than one account sharing that phone number.
    """
    matches = []
    for candidate in find_login_candidates(identifier):
        user = authenticate(request, email=candidate.email, password=password)
        if user is not None:
            matches.append(user)
    if len(matches) > 1:
        return AMBIGUOUS
    return matches[0] if matches else None
