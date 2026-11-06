"""
The public home page. Its numbers come from the database: it used to show
"500+ workers, 300+ jobs completed, 98% satisfaction", none of which was true.
"""
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse


# the partner logos shown on the home page (Yas & Mixx, EzeeMoney, Azam Pesa,
# Equity Bank, Mobile Money, Tracksol, Zati, Zato, Mozeti)
PARTNER_COUNT = 9


def _stats():
    stats = cache.get('home_stats_v2')
    if stats is None:
        from jobs.service_request_models import ServiceRequest
        from workers.models import Category, WorkerProfile

        verified = Q(workers__verification_status='verified', workers__user__is_active=True)
        categories = list(Category.objects.filter(is_active=True)
                          .annotate(verified_workers=Count('workers', filter=verified, distinct=True))
                          .order_by('-verified_workers', 'name'))
        from workers.cities import city_key
        cities = {city_key(c) for c in WorkerProfile.objects.filter(user__is_active=True)
                  .exclude(city='').values_list('city', flat=True)} - {''}
        stats = {
            'verified_workers': WorkerProfile.objects.filter(verification_status='verified', user__is_active=True).count(),
            'registered_workers': WorkerProfile.objects.filter(user__is_active=True).count(),
            'cities_served': len(cities),
            'categories': categories,
            'jobs_done': ServiceRequest.objects.filter(status='completed').count(),
        }
        cache.set('home_stats_v2', stats, 600)  # ten minutes is fresh enough for a front page
    return stats


# Categories carry no icon, so pick one from the name.
_ICONS = (
    (('carpent', 'furniture', 'ceiling'), 'bi-hammer'), (('mason', 'construction', 'tiler', 'steel', 'roof', 'scaffold', 'concrete'), 'bi-bricks'),
    (('electric', 'solar', 'generator'), 'bi-lightning-charge'), (('plumb', 'irrigation', 'pool'), 'bi-droplet'),
    (('clean', 'maid', 'house', 'laundry'), 'bi-stars'), (('driver', 'rider', 'bodaboda', 'delivery'), 'bi-car-front'),
    (('it ', 'computer', 'software', 'network', 'developer', 'data'), 'bi-pc-display'), (('paint', 'decorat'), 'bi-brush'),
    (('weld',), 'bi-fire'), (('mechanic', 'technician', 'repair'), 'bi-wrench-adjustable'), (('chef', 'cook', 'baker', 'cater', 'waiter'), 'bi-cup-hot'),
    (('garden', 'farm', 'tree', 'agri'), 'bi-flower1'), (('security', 'guard', 'gatekeeper'), 'bi-shield-lock'),
    (('hair', 'barber', 'beaut', 'makeup', 'nail'), 'bi-scissors'), (('tailor', 'fashion'), 'bi-person-standing-dress'),
)


def _icon(name):
    name = f'{(name or "").lower()} '
    for words, icon in _ICONS:
        if any(w in name for w in words):
            return icon
    return 'bi-tools'


def home(request):
    user = request.user
    # "Book a worker" goes straight to booking for a signed-in client,
    # and to client sign-up for everyone else (it used to open the login page)
    if user.is_authenticated and getattr(user, 'user_type', '') == 'client':
        book_url = reverse('service_requests_web:client_request_service')
    else:
        book_url = reverse('accounts:client_register')

    stats = _stats()
    popular = [c for c in stats['categories'] if c.verified_workers][:8] or stats['categories'][:8]
    for category in popular:
        category.bi = _icon(category.name)
    return render(request, 'http_landing.html', {
        'verified_workers': stats['verified_workers'],
        'registered_workers': stats['registered_workers'],
        'cities_served': stats['cities_served'],
        'partner_count': PARTNER_COUNT,
        'category_count': len(stats['categories']),
        'jobs_done': stats['jobs_done'],
        'popular_categories': popular,
        'book_url': book_url,
    })
