from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomViewSet, TagViewSet, IngredientViewSet, RecipeViewSet,
    ShoppingCartViewSet, SubscriptionViewSet
)

router = DefaultRouter()
router.register(r'users', CustomViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')
#router.register(r'shopping_cart', ShoppingCartViewSet, basename='shopping_cart')
router.register(r'users/subscriptions', SubscriptionViewSet, basename='subscriptions')
#router.register(r'users/subscriptions', SubscriptionViewSet, basename='subscriptions')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
