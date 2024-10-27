from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from foodgram.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                             ShoppingCart, Subscription, Tag)

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeCreateSerializer, RecipeReadSerializer,
                          ShortRecipeSerializer, SubscriptionActionSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserDetailSerializer)
from .utils import generate_pdf

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class FoodgramUserViewSet(UserViewSet):
    serializer_class = UserDetailSerializer
    pagination_class = CustomPagination
    permission_classes = [AllowAny]

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(
            User.objects.annotate(
                recipes_count=Count('recipes')
            ), id=id
        )

        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'detail': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Subscription.objects.filter(
                user=request.user,
                subscribed_to=author
            ).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            Subscription.objects.create(
                user=request.user,
                subscribed_to=author
            )

            serializer = UserDetailSerializer(
                author,
                context={'request': request}
            )
            user_data = serializer.data  # для постма
            # для постман
            recipes_limit = request.query_params.get('recipes_limit')
            recipes = (
                author.recipes.all()[:int(recipes_limit)]
                if recipes_limit
                else author.recipes.all()
            )
            user_data['recipes'] = ShortRecipeSerializer(
                recipes,
                many=True,
                context={'request': request}
            ).data

            user_data['recipes_count'] = author.recipes.count()  # для постман

            return Response(user_data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            deleted_count, _ = Subscription.objects.filter(
                user=request.user,
                subscribed_to=author
            ).delete()

            if deleted_count == 0:
                return Response(
                    {'detail': 'Подписка не существует.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

    def add_subscription(self, request, author):
        author = get_object_or_404(
            User.objects.annotate(recipes_count=Count('recipes')),
            id=author.id
        )

        data = {'user': request.user.id, 'subscribed_to': author.id}
        serializer = SubscriptionActionSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user_data = UserDetailSerializer(
            author, context={'request': request}
        ).data

        return Response(user_data, status=status.HTTP_201_CREATED)

    def remove_subscription(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)

        deleted_count, _ = Subscription.objects.filter(
            user=request.user,
            subscribed_to=author
        ).delete()

        if deleted_count == 0:
            return Response(
                {'detail': 'Подписка не существует.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        authors = User.objects.filter(subscribers__user=request.user).annotate(
            recipes_count=Count('recipes')
        )

        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        user.avatar.delete(save=True)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPagination
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeReadSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        base_url = getattr(
            settings,
            'SHORT_LINK_BASE_URL',
            'http://localhost:8000/'
        )
        short_link = f'{base_url}{recipe.short_link_hash}'
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    def add_to_collection(self, request, pk, model, error_message):
        recipe = get_object_or_404(Recipe, pk=pk)

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {'detail': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        model.objects.create(user=request.user, recipe=recipe)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_collection(self, request, pk, model, error_message):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()

        if deleted_count == 0:
            return Response(
                {'detail': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self.add_to_collection(
            request,
            pk,
            ShoppingCart,
            'Этот рецепт уже в корзине.'
        )

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        return self.remove_from_collection(
            request,
            pk,
            ShoppingCart,
            'Рецепт не найден в корзине.'
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self.add_to_collection(
            request,
            pk,
            Favorite,
            'Этот рецепт уже в избранном.'
        )

    @favorite.mapping.delete
    def remove_from_favorite(self, request, pk=None):
        return self.remove_from_collection(
            request,
            pk,
            Favorite,
            'Рецепт не найден в избранном.'
        )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_cart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        return generate_pdf(user, ingredients)
