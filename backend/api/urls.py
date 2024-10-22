from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomViewSet, IngredientViewSet, RecipeViewSet, TagViewSet

router = DefaultRouter()
router.register(r'users', CustomViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
