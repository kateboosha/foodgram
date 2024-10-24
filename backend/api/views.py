from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters as rest_framework_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from foodgram.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                             ShoppingCart, Subscription, Tag)

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, ShoppingCartSerializer,
                          ShortRecipeSerializer, SubscriptionActionSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserDetailSerializer)
from .utils import generate_pdf

User = get_user_model()


def redirect_to_recipe(request, short_link):
    recipe = get_object_or_404(Recipe, short_link_hash=short_link)
    full_url = request.build_absolute_uri(f'/recipes/{recipe.id}/')
    return redirect(full_url)


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
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)

        if request.method == "POST":
            if author == request.user:
                return Response(
                    {"detail": "Нельзя подписаться на самого себя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Subscription.objects.filter(
                user=request.user,
                subscribed_to=author
            ).exists():
                return Response(
                    {"detail": "Вы уже подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            Subscription.objects.create(
                user=request.user,
                subscribed_to=author
            )

            serializer = UserDetailSerializer(
                author,
                context={"request": request}
            )
            data = serializer.data

            recipes_limit = request.query_params.get("recipes_limit")
            recipes = (
                author.recipes.all()[:int(recipes_limit)]
                if recipes_limit else author.recipes.all()
            )

            data["recipes"] = ShortRecipeSerializer(
                recipes,
                many=True,
                context={"request": request}
            ).data
            data["recipes_count"] = author.recipes.count()

            return Response(data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            subscription = Subscription.objects.filter(
                user=request.user,
                subscribed_to=author
            )

            if not subscription.exists():
                return Response(
                    {"detail": "Подписка не существует."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subscription.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

    def add_subscription(self, request, author):
        data = {'user': request.user.id, 'subscribed_to': author.id}
        serializer = SubscriptionActionSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        author_with_recipes = User.objects.annotate(
            recipes_count=Count('recipes')
        ).get(id=author.id)

        user_data = UserDetailSerializer(
            author_with_recipes, context={"request": request}
        ).data
        recipes_limit = request.query_params.get("recipes_limit")
        recipes = (
            author.recipes.all()[:int(recipes_limit)]
            if recipes_limit else author.recipes.all()
        )

        user_data["recipes"] = ShortRecipeSerializer(
            recipes,
            many=True,
            context={"request": request}
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
                {"detail": "Подписка не существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        authors = User.objects.filter(subscribers__user=request.user).annotate(
            recipes_count=Count('recipes')
        )

        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            authors,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)

    def get_permissions(self):
        print(self.permission_classes)
        if self.action == "me":
            return [IsAuthenticated()]
        permissions = super().get_permissions()
        print(permissions)
        return permissions

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        user = request.user

        if request.method == "PUT":
            serializer = AvatarSerializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "DELETE":
            user.avatar.delete(save=True)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    filter_backends = (
        DjangoFilterBackend,
        rest_framework_filters.SearchFilter,
        rest_framework_filters.OrderingFilter,
    )
    filterset_class = RecipeFilter
    search_fields = ("^name",)
    pagination_class = CustomPagination
    permission_classes = [IsAuthorOrReadOnly]

    def get_permissions(self):
        # для постман
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeReadSerializer

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        base_url = getattr(
            settings,
            "SHORT_LINK_BASE_URL",
            "http://localhost:8000/"
        )
        short_link = f"{base_url}{recipe.short_link_hash}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists():
            return Response(
                {"detail": "Рецепт уже добавлен в корзину."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ShoppingCartSerializer(
            data={"user": request.user.id, "recipe": recipe.id},
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ShortRecipeSerializer(
            recipe,
            context={"request": request}
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated]
    )
    def remove_from_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        item = ShoppingCart.objects.filter(user=request.user, recipe=recipe)

        if not item.exists():
            return Response(
                {"detail": "Рецепт не был добавлен в корзину."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = item.delete()

        if deleted_count == 0:
            return Response(
                {"detail": "Рецепт не найден в корзине."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт уже добавлен в избранное."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FavoriteSerializer(
            data={"user": request.user.id, "recipe": recipe.id},
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ShortRecipeSerializer(
            recipe,
            context={"request": request}
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated]
    )
    def remove_from_favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        item = Favorite.objects.filter(user=request.user, recipe=recipe)

        if not item.exists():
            return Response(
                {"detail": "Рецепт не был добавлен в избранное."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = item.delete()

        if deleted_count == 0:
            return Response(
                {"detail": "Рецепт не найден в избранном."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart"
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_cart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )
        return generate_pdf(user, ingredients)


"""

Попытки реализовать по правкам код.
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self.add_to_list(request, pk, ShoppingCart)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self.add_to_list(request, pk, Favorite)

    def add_to_list(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт уже добавлен."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(
            data={"user": request.user.id, "recipe": recipe.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ShortRecipeSerializer(
            recipe,
            context={"request": request}
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated],
        url_path="remove-from-list"
    )
    def remove_from_list(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        item = model.objects.filter(user=request.user, recipe=recipe)

        if item.exists():
            item.delete()
            return Response(
                {"status": "уничтожено!"},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {"status": "не найдено"},
            status=status.HTTP_400_BAD_REQUEST
        )

    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_cart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )
        return generate_pdf(user, ingredients)
"""
