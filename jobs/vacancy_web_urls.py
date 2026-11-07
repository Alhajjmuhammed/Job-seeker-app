"""Website pages for job posts (namespace 'vacancies') - see jobs/vacancy_web_views.py."""
from django.urls import path

from . import vacancy_web_views as v

urlpatterns = [
    path('', v.board, name='board'),
    path('post/', v.post, name='post'),
    path('mine/', v.mine, name='mine'),
    path('my-applications/', v.my_applications, name='my_applications'),
    path('contracts/', v.contracts, name='contracts'),
    path('contracts/<int:pk>/', v.contract, name='contract'),
    path('contracts/<int:pk>/<str:action>/', v.contract_action, name='contract_action'),
    path('applications/<int:pk>/<str:action>/', v.application_action, name='application_action'),
    path('review/', v.review_queue, name='review_queue'),
    path('all/', v.admin_all, name='admin_all'),
    path('<int:pk>/', v.detail, name='detail'),
    path('<int:pk>/edit/', v.post, name='edit'),
    path('<int:pk>/apply/', v.apply, name='apply'),
    path('<int:pk>/close/', v.close, name='close'),
    path('<int:pk>/review/', v.review, name='review'),
    path('<int:pk>/report/', v.report, name='report'),
]
