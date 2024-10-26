from django.urls import path

from .views import redirect_to_recipe

urlpatterns = [
    path(
        's/<str:short_link>/',
        redirect_to_recipe,
        name='short_link_redirect'
    ),
]
