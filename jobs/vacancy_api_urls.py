"""App API for job posts - see jobs/vacancy_api.py."""
from django.urls import path

from . import vacancy_api as api

urlpatterns = [
    path('', api.vacancies, name='vacancy_list'),
    path('options/', api.options, name='vacancy_options'),
    path('mine/', api.mine, name='vacancy_mine'),
    path('review/', api.review_queue, name='vacancy_review_queue'),
    path('my-applications/', api.my_applications, name='vacancy_my_applications'),
    path('contracts/', api.contracts, name='vacancy_contracts'),
    path('contracts/<int:pk>/', api.contract_detail, name='vacancy_contract_detail'),
    path('contracts/<int:pk>/<str:action>/', api.contract_action, name='vacancy_contract_action'),
    path('applications/<int:pk>/<str:action>/', api.application_action, name='vacancy_application_action'),
    path('<int:pk>/', api.vacancy_detail, name='vacancy_detail'),
    path('<int:pk>/close/', api.close, name='vacancy_close'),
    path('<int:pk>/apply/', api.apply, name='vacancy_apply'),
    path('<int:pk>/report/', api.report_vacancy, name='vacancy_report'),
    path('<int:pk>/applications/', api.applications, name='vacancy_applications'),
    path('<int:pk>/review/', api.review, name='vacancy_review'),
]
