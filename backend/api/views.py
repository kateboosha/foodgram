import hashlib

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from foodgram.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                             ShoppingCart, Subscription, Tag)
from .pagination import CustomPagination
from .serializers import (AvatarSerializer, UserDetailSerializer, SubscriptionActionSerializer,
                          FavoriteSerializer, IngredientSerializer,
                          ShortRecipeSerializer, TagSerializer,
                          )


User = get_user_model()


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Ingredient
        fields = ["name"]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class FoodgramUserViewSet(UserViewSet):
    serializer_class = UserDetailSerializer
    pagination_class = CustomPagination
    permission_classes = (AllowAny,)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)

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

        Subscription.objects.create(user=request.user, subscribed_to=author)

        serializer = UserDetailSerializer(author, context={"request": request})
        data = serializer.data

        recipes_limit = request.query_params.get("recipes_limit")
        recipes = author.recipes.all()[:int(recipes_limit)] if recipes_limit else author.recipes.all()

        data["recipes"] = ShortRecipeSerializer(
            recipes,
            many=True,
            context={"request": request}
        ).data
        data["recipes_count"] = author.recipes.count()

        return Response(data, status=status.HTTP_201_CREATED)
    
    def add_subscription(self, request, author):
        data = {'user': request.user.id, 'subscribed_to': author.id}
        serializer = SubscriptionActionSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        author_with_recipes = User.objects.annotate(recipes_count=Count('recipes')).get(id=author.id)

        user_data = UserDetailSerializer(author_with_recipes, context={"request": request}).data
        recipes_limit = request.query_params.get("recipes_limit")
        recipes = author.recipes.all()[:int(recipes_limit)] if recipes_limit else author.recipes.all()

        user_data["recipes"] = ShortRecipeSerializer(
            recipes,
            many=True,
            context={"request": request}
        ).data

        return Response(user_data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def remove_subscription(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        subscription = Subscription.objects.filter(
            user=request.user,
            subscribed_to=author
        ).first()

        if not subscription:
            if not User.objects.filter(id=author.id).exists():
                return Response(
                    {"detail": "Пользователь не найден."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"detail": "Подписка не существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        user = request.user
        subscriptions = Subscription.objects.filter(
            user=user
        ).select_related("subscribed_to")
        authors = [sub.subscribed_to for sub in subscriptions]

        recipes_limit = request.query_params.get("recipes_limit")
        results = []
        for author in authors:
            recipes = author.recipes.all()[:int(recipes_limit)] if recipes_limit else author.recipes.all()

            author_data = UserDetailSerializer(
                author,
                context={"request": request}
            ).data
            author_data["recipes"] = ShortRecipeSerializer(
                recipes,
                many=True,
                context={"request": request}
            ).data
            author_data["recipes_count"] = author.recipes.count()

            results.append(author_data)

        page = self.paginate_queryset(results)
        if page is not None:
            return self.get_paginated_response(page)

        return Response({"results": results})

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = UserDetailSerializer(
            request.user,
            context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        user = request.user

        if request.method == "PUT":
            if "avatar" not in request.data or request.data["avatar"] is None:
                return Response(
                    {"avatar": ["Это поле не может быть пустым."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AvatarSerializer(
                user,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.avatar.delete(save=True)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ("author", "tags__slug")
    search_fields = ("^name",)
    pagination_class = CustomPagination
    permission_classes_by_action = {
        "list": (AllowAny,),
        "retrieve": (AllowAny,),
        "create": (IsAuthenticated,),
        "update": (IsAuthenticated,),
        "partial_update": (IsAuthenticated,),
        "destroy": (IsAuthenticated,),
    }

    def get_permissions(self):
        return [
            permission()
            for permission in self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        ]

    def get_queryset(self):
        queryset = Recipe.objects.all()
        user = self.request.user

        is_favorited = self.request.query_params.get("is_favorited")
        if is_favorited and user.is_authenticated:
            if is_favorited == "1":
                queryset = queryset.filter(favorites__user=user)
            elif is_favorited == "0":
                queryset = queryset.exclude(favorites__user=user)

        is_in_shopping_cart = self.request.query_params.get(
            "is_in_shopping_cart"
        )
        if is_in_shopping_cart and user.is_authenticated:
            if is_in_shopping_cart == "1":
                queryset = queryset.filter(shoppingcart__user=user)
            elif is_in_shopping_cart == "0":
                queryset = queryset.exclude(shoppingcart__user=user)

        tags = self.request.query_params.getlist("tags")
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.author != request.user:
            return Response(
                {"detail": "Вы не можете обновить чужой рецепт."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.author != request.user:
            return Response(
                {"detail": "Вы не можете удалить чужой рецепт."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:6]
        base_url = getattr(
            settings,
            "SHORT_LINK_BASE_URL",
            "http://localhost:8000/"
        )
        short_link = f"{base_url}{short_link_hash}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        if request.method == "POST":
            return self.add_to_cart(request, pk)
        return self.remove_from_cart(request, pk)

    def add_to_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()

        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {"detail": "Recipe is already in the shopping cart."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ShoppingCart.objects.create(user=user, recipe=recipe)
        recipe_data = ShoppingCartRecipeSerializer(
            recipe,
            context={"request": request}
        ).data
        return Response(recipe_data, status=status.HTTP_201_CREATED)

    def remove_from_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()
        cart_item = ShoppingCart.objects.filter(
            user=user,
            recipe=recipe
        ).first()

        if cart_item:
            cart_item.delete()
            return Response(
                {"status": "removed from cart"},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {"status": "not in cart"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == "POST":
            return self.add_to_favorites(user, recipe)
        elif request.method == "DELETE":
            return self.remove_from_favorites(user, recipe)

    def add_to_favorites(self, user, recipe):
        serializer = FavoriteSerializer(
            data={"recipe": recipe},
            context={"request": self.request, "recipe": recipe}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_serializer = ShortRecipeSerializer(
            recipe,
            context={"request": self.request}
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def remove_from_favorites(self, user, recipe):
        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response(
                {"status": "удалено из избранного"},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {"status": "Не в избранном"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart"
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart.pdf"'
        )

        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))

        p = canvas.Canvas(response, pagesize=letter)
        p.setFont("DejaVuSans", 12)
        _, height = letter
        y = height - 40

        p.drawString(
            100, y, f"Список покупок для пользователя: {user.username}"
        )
        y -= 20

        if not shopping_cart_items.exists():
            p.drawString(100, y, "Список покупок пуст.")
            p.showPage()
            p.save()
            return response

        ingredients = {}
        for item in shopping_cart_items:
            recipe = item.recipe
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
            for recipe_ingredient in recipe_ingredients:
                ingredient = recipe_ingredient.ingredient
                amount = recipe_ingredient.amount
                if ingredient.name in ingredients:
                    ingredients[ingredient.name] += amount
                else:
                    ingredients[ingredient.name] = amount

        for ingredient, amount in ingredients.items():
            p.drawString(100, y, f"{ingredient}: {amount}")
            y -= 20
            if y < 40:
                p.showPage()
                p.setFont("DejaVuSans", 12)
                y = height - 40

        p.showPage()
        p.save()

        return response
