"""Custom skills a worker adds to their profile - shared by the website
(workers/views.py custom_skill_add) and the app API (workers/api_views.py)."""
from .forms import CustomSkillForm


def add_custom_skill(profile, data, files=None):
    """Returns (skill, outcome, form). outcome: 'added' | 'exists' | 'invalid'.
    (worker, name) is unique - adding the same skill twice used to be a 500."""
    form = CustomSkillForm(data, files)
    if not form.is_valid():
        return None, 'invalid', form
    skill = form.save(commit=False)
    skill.name = skill.name.strip()
    skill.worker = profile
    existing = profile.custom_skills.filter(name__iexact=skill.name).first()
    if existing:
        return existing, 'exists', form
    skill.save()
    return skill, 'added', form


def skill_json(skill, request=None):
    cert = None
    if skill.certificate:
        try:
            from worker_connect.media_views import signed_media_url
            cert = signed_media_url(request, skill.certificate) if request is not None else skill.certificate.url
        except Exception:
            cert = None
    return {
        'id': skill.id,
        'name': skill.name,
        'description': skill.description,
        'years_of_experience': skill.years_of_experience,
        'is_verified': skill.is_verified,
        'certificate': cert,
        'created_at': skill.created_at.isoformat() if skill.created_at else None,
    }
