from django.urls import path
from .views import users_view, categories_view, expenses_view, monthly_summary_view

urlpatterns = [
    path('users', users_view),  # GET, POST
    path('categories', categories_view),  # GET, POST
    path('expenses', expenses_view),  # GET, POST
    path('reports/monthly_summary', monthly_summary_view),  # GET
]