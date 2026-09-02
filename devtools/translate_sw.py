#!/usr/bin/env python
"""
Fill in Kiswahili for the strings we can translate with confidence.

Drafted, not authoritative. Standard Tanzanian usage is preferred over
Kenyan variants where the two differ. Anything ambiguous, idiomatic, or
carrying legal or financial weight is deliberately left empty so a native
speaker sees it as outstanding work rather than as something already signed
off. An empty msgstr falls back to English, which is safe; a confidently
wrong translation is not.

    python devtools/translate_sw.py --check
    python devtools/translate_sw.py --write
"""
import argparse
import pathlib
import re
import sys

PO = pathlib.Path(__file__).resolve().parent.parent / 'locale/sw/LC_MESSAGES/django.po'

TRANSLATIONS = {
    # --- actions -----------------------------------------------------------
    'Save': 'Hifadhi',
    'Save changes': 'Hifadhi mabadiliko',
    'Save Changes': 'Hifadhi Mabadiliko',
    'Cancel': 'Ghairi',
    'Submit': 'Wasilisha',
    'Search': 'Tafuta',
    'Filter': 'Chuja',
    'Filter:': 'Chuja:',
    'Edit': 'Hariri',
    'Delete': 'Futa',
    'Remove': 'Ondoa',
    'Add': 'Ongeza',
    'Update': 'Sasisha',
    'Close': 'Funga',
    'Back': 'Rudi',
    'Next': 'Ifuatayo',
    'Previous': 'Iliyotangulia',
    'Continue': 'Endelea',
    'Confirm': 'Thibitisha',
    'Accept': 'Kubali',
    'Reject': 'Kataa',
    'Approve': 'Idhinisha',
    'View': 'Angalia',
    'View All': 'Angalia Zote',
    'View Details': 'Angalia Maelezo',
    'Download': 'Pakua',
    'Upload': 'Pakia',
    'Apply': 'Omba',
    'Send': 'Tuma',
    'Retry': 'Jaribu tena',
    'Refresh': 'Onyesha upya',

    # --- accounts ----------------------------------------------------------
    'Login': 'Ingia',
    'Log In': 'Ingia',
    'Logout': 'Toka',
    'Log Out': 'Toka',
    'Register': 'Jisajili',
    'Sign Up': 'Jisajili',
    'Sign In': 'Ingia',
    'Email': 'Barua pepe',
    'Email Address': 'Anwani ya Barua Pepe',
    'Password': 'Nenosiri',
    'New Password': 'Nenosiri Jipya',
    'Current Password': 'Nenosiri la Sasa',
    'Confirm Password': 'Thibitisha Nenosiri',
    'Confirm New Password': 'Thibitisha Nenosiri Jipya',
    'Change Password': 'Badilisha Nenosiri',
    'Forgot Password?': 'Umesahau Nenosiri?',
    'Remember your password?': 'Unakumbuka nenosiri lako?',
    'Back to Login': 'Rudi Kuingia',
    'Send Reset Link': 'Tuma Kiungo cha Kubadilisha',
    'Enter your new password below': 'Weka nenosiri lako jipya hapa chini',
    'Enter your email to receive a password reset link':
        'Weka barua pepe yako ili upokee kiungo cha kubadilisha nenosiri',
    'Update your account password': 'Sasisha nenosiri la akaunti yako',
    'Minimum 8 characters': 'Angalau herufi 8',
    'Invalid Reset Link': 'Kiungo cha Kubadilisha si Sahihi',
    'First Name': 'Jina la Kwanza',
    'Last Name': 'Jina la Ukoo',
    'Full Name': 'Jina Kamili',
    'Username': 'Jina la Mtumiaji',
    'Phone Number': 'Namba ya Simu',
    'Profile': 'Wasifu',
    'My Profile': 'Wasifu Wangu',
    'Edit Profile': 'Hariri Wasifu',
    'Settings': 'Mipangilio',
    'Update your name, contact details and photo.':
        'Sasisha jina lako, mawasiliano na picha.',

    # --- roles and marketplace --------------------------------------------
    'Worker': 'Mfanyakazi',
    'Workers': 'Wafanyakazi',
    'Client': 'Mteja',
    'Clients': 'Wateja',
    'Agent': 'Wakala',
    'Agents': 'Mawakala',
    'Admin': 'Msimamizi',
    'Job': 'Kazi',
    'Jobs': 'Kazi',
    'Service': 'Huduma',
    'Services': 'Huduma',
    'Category': 'Kategoria',
    'Categories': 'Kategoria',
    'Skill': 'Ujuzi',
    'Skills': 'Ujuzi',
    'Request': 'Ombi',
    'Requests': 'Maombi',
    'My Requests': 'Maombi Yangu',
    'Service Request': 'Ombi la Huduma',
    'Service Requests': 'Maombi ya Huduma',
    'Assignment': 'Kazi Uliyopewa',
    'Assignments': 'Kazi Ulizopewa',
    'Experience': 'Uzoefu',
    'Documents': 'Nyaraka',
    'Document': 'Hati',

    # --- status ------------------------------------------------------------
    'Status': 'Hali',
    'Pending': 'Inasubiri',
    'Approved': 'Imeidhinishwa',
    'Rejected': 'Imekataliwa',
    'Accepted': 'Imekubaliwa',
    'Completed': 'Imekamilika',
    'Cancelled': 'Imeghairiwa',
    'In Progress': 'Inaendelea',
    'Active': 'Inatumika',
    'Inactive': 'Haitumiki',
    'Available': 'Yupo',
    'Busy': 'Ana shughuli',
    'Verified': 'Amethibitishwa',
    'Unverified': 'Hajathibitishwa',
    'New': 'Mpya',
    'Read': 'Imesomwa',
    'Unread': 'Haijasomwa',

    # --- money and booking -------------------------------------------------
    'Price': 'Bei',
    'Total': 'Jumla',
    'Total Price': 'Jumla ya Bei',
    'Amount': 'Kiasi',
    'Payment': 'Malipo',
    'Payments': 'Malipo',
    'Paid': 'Imelipwa',
    'Unpaid': 'Haijalipwa',
    'Service Fee': 'Ada ya Huduma',
    'Earnings': 'Mapato',
    'Total Earnings': 'Jumla ya Mapato',
    'Payment Method': 'Njia ya Malipo',
    'Payment Status': 'Hali ya Malipo',
    'Date': 'Tarehe',
    'Start Date': 'Tarehe ya Kuanza',
    'End Date': 'Tarehe ya Kumaliza',
    'Duration': 'Muda',
    'Location': 'Mahali',
    'City': 'Jiji',
    'Address': 'Anwani',
    'Description': 'Maelezo',
    'Title': 'Kichwa',
    'Notes': 'Maelezo ya Ziada',
    'Urgency': 'Uharaka',
    'Normal': 'Kawaida',
    'Urgent': 'Haraka',
    'Emergency': 'Dharura',

    # --- navigation and dashboard -----------------------------------------
    'Dashboard': 'Dashibodi',
    'Home': 'Mwanzo',
    'Notifications': 'Arifa',
    'Messages': 'Ujumbe',
    'Message': 'Ujumbe',
    'History': 'Historia',
    'Activity': 'Shughuli',
    'Overview': 'Muhtasari',
    'Reports': 'Ripoti',
    'Statistics': 'Takwimu',
    'Help': 'Msaada',
    'About': 'Kuhusu',
    'Contact': 'Wasiliana',
    'Rating': 'Ukadiriaji',
    'Reviews': 'Maoni',
    'Review': 'Maoni',
    'Mark All as Read': 'Weka Zote Kama Zimesomwa',
    'Stay updated with your latest activities':
        'Fuatilia shughuli zako za hivi karibuni',
    "You don't have any notifications yet.": 'Bado huna arifa yoyote.',

    # --- common phrases ----------------------------------------------------
    'Loading...': 'Inapakia...',
    'No results found': 'Hakuna matokeo',
    'Not assigned': 'Hajapangiwa',
    'Optional': 'Si lazima',
    'Required': 'Inahitajika',
    'Yes': 'Ndiyo',
    'No': 'Hapana',
    'All': 'Zote',
    'None': 'Hakuna',
    'Actions': 'Vitendo',
    'Details': 'Maelezo',
    'Name': 'Jina',
    'Type': 'Aina',
    'Verification': 'Uthibitisho',
    'Verification Status': 'Hali ya Uthibitisho',
    'Jobs completed': 'Kazi zilizokamilika',
    'Completed Jobs': 'Kazi Zilizokamilika',

    # --- second pass: common UI labels ------------------------------------
    'Administrator': 'Msimamizi',
    'Account Information': 'Taarifa za Akaunti',
    'Additional Information': 'Taarifa za Ziada',
    'Additional Notes': 'Maelezo ya Ziada',
    'Activity History': 'Historia ya Shughuli',
    'All History': 'Historia Yote',
    'All Statuses': 'Hali Zote',
    'All Types': 'Aina Zote',
    'Add Experience': 'Ongeza Uzoefu',
    'Add to Team': 'Ongeza kwenye Timu',
    'Access Forbidden': 'Hauruhusiwi',
    'Accept this job?': 'Ukubali kazi hii?',
    'Personal Information': 'Taarifa Binafsi',
    'Contact Information': 'Taarifa za Mawasiliano',
    'Basic Information': 'Taarifa za Msingi',
    'Payment Information': 'Taarifa za Malipo',
    'Job Details': 'Maelezo ya Kazi',
    'Service Details': 'Maelezo ya Huduma',
    'Worker Details': 'Maelezo ya Mfanyakazi',
    'Client Details': 'Maelezo ya Mteja',
    'My Jobs': 'Kazi Zangu',
    'My Assignments': 'Kazi Nilizopewa',
    'My Earnings': 'Mapato Yangu',
    'My Documents': 'Nyaraka Zangu',
    'My Team': 'Timu Yangu',
    'Available Workers': 'Wafanyakazi Waliopo',
    'Assigned Workers': 'Wafanyakazi Waliopangwa',
    'Assigned Worker': 'Mfanyakazi Aliyepangwa',
    'Assign Worker': 'Panga Mfanyakazi',
    'Select Worker': 'Chagua Mfanyakazi',
    'Select Category': 'Chagua Kategoria',
    'Select a category': 'Chagua kategoria',
    'Choose a worker': 'Chagua mfanyakazi',
    'Number of Workers': 'Idadi ya Wafanyakazi',
    'Workers Needed': 'Wafanyakazi Wanaohitajika',
    'Start Time': 'Muda wa Kuanza',
    'End Time': 'Muda wa Kumaliza',
    'Preferred Date': 'Tarehe Unayopendelea',
    'Preferred Time': 'Muda Unaopendelea',
    'Daily Rate': 'Kiwango cha Kila Siku',
    'Amount Paid': 'Kiasi Kilicholipwa',
    'Amount Due': 'Kiasi Kinachodaiwa',
    'Grand Total': 'Jumla Kuu',
    'Subtotal': 'Jumla Ndogo',
    'Invoice': 'Ankara',
    'Receipt': 'Risiti',
    'Reference': 'Kumbukumbu',
    'Transaction': 'Muamala',
    'Mobile Money': 'Pesa ya Simu',
    'Card': 'Kadi',
    'Cash': 'Fedha Taslimu',
    'Bank': 'Benki',
    'Balance': 'Salio',
    'Withdraw': 'Toa Pesa',
    'Deposit': 'Weka Pesa',
    'Clock In': 'Ingia Kazini',
    'Clock Out': 'Toka Kazini',
    'Hours Worked': 'Saa Zilizofanyika',
    'Start Work': 'Anza Kazi',
    'Complete Work': 'Maliza Kazi',
    'Mark as Complete': 'Weka Kama Imekamilika',
    'In Review': 'Inakaguliwa',
    'Waiting': 'Inasubiri',
    'Assigned': 'Imepangwa',
    'Declined': 'Imekataliwa',
    'Expired': 'Imeisha muda',
    'Draft': 'Rasimu',
    'Sent': 'Imetumwa',
    'Received': 'Imepokelewa',
    'Today': 'Leo',
    'Yesterday': 'Jana',
    'Tomorrow': 'Kesho',
    'This Week': 'Wiki Hii',
    'This Month': 'Mwezi Huu',
    'Last Week': 'Wiki Iliyopita',
    'Last Month': 'Mwezi Uliopita',
    'Day': 'Siku',
    'Days': 'Siku',
    'Week': 'Wiki',
    'Month': 'Mwezi',
    'Year': 'Mwaka',
    '3 Months': 'Miezi 3',
    '6 Months': 'Miezi 6',
    'Region': 'Mkoa',
    'District': 'Wilaya',
    'Street': 'Mtaa',
    'Country': 'Nchi',
    'Gender': 'Jinsia',
    'Male': 'Mume',
    'Female': 'Mke',
    'Age': 'Umri',
    'Date of Birth': 'Tarehe ya Kuzaliwa',
    'National ID': 'Kitambulisho cha Taifa',
    'Photo': 'Picha',
    'Profile Photo': 'Picha ya Wasifu',
    'Upload Document': 'Pakia Hati',
    'Rejected Documents': 'Nyaraka Zilizokataliwa',
    'Search...': 'Tafuta...',
    'No data': 'Hakuna taarifa',
    'No data available': 'Hakuna taarifa zilizopo',
    'Nothing here yet': 'Bado hakuna kitu',
    'Try again': 'Jaribu tena',
    'Something went wrong': 'Kuna hitilafu imetokea',
    'Are you sure?': 'Una uhakika?',
    'This cannot be undone': 'Hii haiwezi kutenduliwa',
    'Success': 'Imefanikiwa',
    'Error': 'Hitilafu',
    'Warning': 'Onyo',
    'Information': 'Taarifa',
    'Print': 'Chapisha',
    'Export': 'Hamisha',
    'Share': 'Shiriki',
    'Copy': 'Nakili',
    'Select': 'Chagua',
    'Select All': 'Chagua Zote',
    'Clear': 'Futa',
    'Reset': 'Anzisha upya',
    'Show': 'Onyesha',
    'Hide': 'Ficha',
    'More': 'Zaidi',
    'Less': 'Kidogo',
    'Open': 'Fungua',
    'Sign Out': 'Toka',
    'Welcome': 'Karibu',
    'Welcome back': 'Karibu tena',
    'Language': 'Lugha',
    'Terms of Service': 'Masharti ya Huduma',
    'Privacy Policy': 'Sera ya Faragha',
}


def load(text):
    """Every msgid/msgstr pair, with the span of the msgstr line."""
    pattern = re.compile(r'^msgid "((?:[^"\\]|\\.)*)"\n^msgstr "((?:[^"\\]|\\.)*)"',
                         re.M)
    return list(pattern.finditer(text))


def normalise(text):
    """Fold the differences that are not differences of meaning."""
    return re.sub(r'\s+', ' ', text).strip().rstrip(':*').strip().lower()


NORMALISED = {normalise(k): v for k, v in TRANSLATIONS.items()}


def lookup(msgid):
    """Exact match first, then case and trailing-punctuation insensitive.

    Only single words and short labels go through the loose path - a longer
    sentence that merely starts the same way is a different sentence, and
    guessing at it is how a translation ends up confidently wrong.
    """
    if msgid in TRANSLATIONS:
        return TRANSLATIONS[msgid]
    key = normalise(msgid)
    if key in NORMALISED and len(key) <= 40:
        translated = NORMALISED[key]
        # keep the original's trailing colon, which is usually layout
        if msgid.rstrip().endswith(':'):
            return translated + ':'
        return translated
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    text = PO.read_text()
    filled = already = unknown = 0
    out, cursor = [], 0

    for m in load(text):
        msgid, msgstr = m.group(1), m.group(2)
        if not msgid:
            continue
        if msgstr:
            already += 1
            continue
        translation = lookup(msgid)
        if translation is None:
            unknown += 1
            continue
        filled += 1
        out.append(text[cursor:m.start(2)])
        out.append(translation)
        cursor = m.end(2)

    out.append(text[cursor:])
    result = ''.join(out)

    print(f'  already translated: {already}')
    print(f'  filled in now:      {filled}')
    print(f'  still needing a speaker: {unknown}')
    if args.write:
        PO.write_text(result)
        print('  written')
    return 0


if __name__ == '__main__':
    sys.exit(main())
