from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomUserViewSet, TagViewSet, IngredientViewSet, RecipeViewSet,
    FavoriteViewSet, ShoppingCartViewSet
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'favorites', FavoriteViewSet, basename='favorites')
router.register(r'shopping_cart', ShoppingCartViewSet, basename='shopping_cart')

urlpatterns = [
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    path('api/', include(router.urls)),
]