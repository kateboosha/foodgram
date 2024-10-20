from django.core.files.base import ContentFile
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import hashlib
from django.shortcuts import get_object_or_404
from django.conf import settings
import base64
from djoser.views import UserViewSet
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from foodgram.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag, Subscription, User
from .serializers import (CustomUserSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeSerializer,
                          TagSerializer, UserRegistrationSerializer, AvatarSerializer,
                          SubscriptionSerializer,
                        )
from .pagination import CustomPagination


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение, позволяющее редактировать объект только его автору."""

    def has_object_permission(self, request, view, obj):
        # Разрешить доступ к объекту, если это безопасный метод (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Разрешить доступ, если пользователь является автором объекта
        return obj.author == request.user


class CustomViewSet(UserViewSet):
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination
    permission_classes_by_action = {
        "create": (AllowAny,),
        "list": (AllowAny,),
        "retrieve": (AllowAny,),
        "set_password": (IsAuthenticated,),
    }

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)

        if author == request.user:
            return Response(
                {"detail": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, есть ли уже подписка на этого пользователя
        if Subscription.objects.filter(user=request.user, subscribed_to=author).exists():
            return Response(
                {"detail": "Вы уже подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создание подписки
        Subscription.objects.create(user=request.user, subscribed_to=author)

        # Сериализуем данные автора
        serializer = CustomUserSerializer(author, context={'request': request})
        data = serializer.data

        # Получаем список рецептов автора с лимитом, если указан
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit is not None:
            recipes = author.recipes.all()[:int(recipes_limit)]
        else:
            recipes = author.recipes.all()

        data['recipes'] = RecipeSerializer(recipes, many=True, context={'request': request}).data
        data['recipes_count'] = author.recipes.count()

        # Возвращаем корректный статус 201
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        """Получаем список пользователей, на которых подписан текущий пользователь."""
        user = request.user
        subscriptions = Subscription.objects.filter(user=user).select_related('subscribed_to')
        authors = [sub.subscribed_to for sub in subscriptions]

        # Получаем параметр recipes_limit из запроса, если он существует
        recipes_limit = request.query_params.get('recipes_limit')

        # Подготовка данных для каждого автора
        results = []
        for author in authors:
         # Ограничиваем количество рецептов, если указано recipes_limit
            if recipes_limit is not None:
                recipes = author.recipes.all()[:int(recipes_limit)]
            else:
                recipes = author.recipes.all()

        # Формируем данные для каждого автора с учетом рецептов и их количества
            author_data = CustomUserSerializer(author, context={'request': request}).data
            author_data['recipes'] = RecipeSerializer(recipes, many=True, context={'request': request}).data
            author_data['recipes_count'] = author.recipes.count()

            results.append(author_data)

    # Пагинация
        page = self.paginate_queryset(results)
        if page is not None:
            return self.get_paginated_response(page)

        return Response({'results': results})

    def create(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        return [
            permission() for permission in self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        ]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {"current_password": ["Обязательное поле."],
                 "new_password": ["Обязательное поле."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        if not user.check_password(current_password):
            return Response(
                {"detail": "Текущий пароль неверен."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = CustomUserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar', permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            if 'avatar' not in request.data or request.data['avatar'] is None:
                return Response(
                    {"avatar": ["Это поле не может быть пустым."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = AvatarSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            user.avatar.delete(save=True)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


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

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('author', 'tags__slug')
    search_fields = ('^name',)
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
            permission() for permission in self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        ]

    def get_queryset(self):
        """Фильтрует рецепты по параметрам is_favorited, is_in_shopping_cart и tags."""
        queryset = Recipe.objects.all()
        user = self.request.user

    # Фильтрация по параметру is_favorited
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited and user.is_authenticated:
            if is_favorited == '1':
                queryset = queryset.filter(favorites__user=user)
            elif is_favorited == '0':
                queryset = queryset.exclude(favorites__user=user)

    # Фильтрация по параметру is_in_shopping_cart
        is_in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart and user.is_authenticated:
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(shoppingcart__user=user)
            elif is_in_shopping_cart == '0':
                queryset = queryset.exclude(shoppingcart__user=user)

    # Фильтрация по тегам (логика "ИЛИ")
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверка на права доступа: только автор может обновить рецепт
        if instance.author != request.user:
            return Response({"detail": "Вы не имеете права обновлять этот рецепт."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Обеспечим корректную структуру данных при возврате ответа
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Переопределяем метод удаления рецепта."""
        instance = self.get_object()

        # Проверка на права доступа: только автор может удалить рецепт
        if instance.author != request.user:
            return Response({"detail": "Вы не можете удалить чужой рецепт."},
                            status=status.HTTP_403_FORBIDDEN)

        # Удаление собственного рецепта
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Генерация короткой ссылки для рецепта."""
        recipe = self.get_object()

        # Генерация уникальной строки на основе ID рецепта
        short_link_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:6]

        # Получаем базовый URL для короткой ссылки из настроек
        base_url = getattr(settings, 'SHORT_LINK_BASE_URL', 'http://localhost:8000/')
        
        # Сформируем короткую ссылку
        short_link = f"{base_url}{short_link_hash}"

        # Вернем результат
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из корзины."""
        if request.method == 'POST':
            return self.add_to_cart(request, pk)
        return self.remove_from_cart(request, pk)

    def add_to_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()
        # Проверка, есть ли уже рецепт в корзине
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({"detail": "Recipe is already in the shopping cart."}, status=status.HTTP_400_BAD_REQUEST)

        # Если рецепт не в корзине, добавляем его
        ShoppingCart.objects.create(user=user, recipe=recipe)
        return Response({"status": "added to cart"}, status=status.HTTP_201_CREATED)

    def remove_from_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()
        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe).first()

        if cart_item:
            cart_item.delete()
            return Response({"status": "removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"status": "not in cart"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            return self.add_to_favorites(user, recipe)
        elif request.method == 'DELETE':
            return self.remove_from_favorites(user, recipe)

    def add_to_favorites(self, user, recipe):
        """Логика добавления рецепта в избранное."""
        serializer = FavoriteSerializer(data={'recipe': recipe}, context={'request': self.request, 'recipe': recipe})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Вернем детализированную информацию о рецепте
        response_serializer = RecipeSerializer(recipe, context={'request': self.request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorites(self, user, recipe):
        """Логика удаления рецепта из избранного."""
        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response({"status": "removed from favorites"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"status": "not in favorites"}, status=status.HTTP_400_BAD_REQUEST)




    
        """ 

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        
        return Subscription.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        subscribed_to_id = request.data.get('subscribed_to')
        subscribed_to = get_object_or_404(User, id=subscribed_to_id)

        if request.user == subscribed_to:
            return Response({"detail": "Нельзя подписаться на самого себя."}, status=status.HTTP_400_BAD_REQUEST)

        if Subscription.objects.filter(user=request.user, subscribed_to=subscribed_to).exists():
            return Response({"detail": "Вы уже подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)


        subscription = Subscription.objects.create(user=request.user, subscribed_to=subscribed_to)
        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        было в рецептах

            @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, pk=None):

        user = request.user
        author = get_object_or_404(User, pk=pk)

        subscription = Subscription.objects.filter(user=user, subscribed_to=author).first()

        # Проверка на наличие подписки
        if subscription:
            subscription.delete()
            return Response({"status": "unsubscribed"}, status=status.HTTP_204_NO_CONTENT)

        # Обработка попытки удалить несуществующую подписку
        return Response({"status": "Subscription not found"}, status=status.HTTP_400_BAD_REQUEST)
        class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('author', 'tags__slug')
    search_fields = ('^name',)
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
            permission() for permission in self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        ]

    def get_queryset(self):
   
        queryset = Recipe.objects.all()
        user = self.request.user
        is_favorited = self.request.query_params.get('is_favorited')

        if is_favorited and user.is_authenticated:
            if is_favorited == '1':
                queryset = queryset.filter(favorites__user=user)
            elif is_favorited == '0':
                queryset = queryset.exclude(favorites__user=user)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверка на права доступа: только автор может обновить рецепт
        if instance.author != request.user:
            return Response({"detail": "Вы не имеете права обновлять этот рецепт."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Обеспечим корректную структуру данных при возврате ответа
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def get_link(self, request, pk=None):
  
        recipe = self.get_object()

        # Генерация уникальной строки на основе ID рецепта
        short_link_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:6]

        # Получаем базовый URL для короткой ссылки из настроек
        base_url = getattr(settings, 'SHORT_LINK_BASE_URL', 'http://localhost:8000/')
        
        # Сформируем короткую ссылку без 's'
        short_link = f"{base_url}{short_link_hash}"

        # Вернем результат
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):

        if request.method == 'POST':
            return self.add_to_cart(request, pk)
        return self.remove_from_cart(request, pk)

    def add_to_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()
        # Проверка, есть ли уже рецепт в корзине
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({"detail": "Recipe is already in the shopping cart."}, status=status.HTTP_400_BAD_REQUEST)

        # Если рецепт не в корзине, добавляем его
        ShoppingCart.objects.create(user=user, recipe=recipe)
        return Response({"status": "added to cart"}, status=status.HTTP_201_CREATED)

    def remove_from_cart(self, request, pk):
        user = request.user
        recipe = self.get_object()
        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe).first()

        if cart_item:
            cart_item.delete()
            return Response({"status": "removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"status": "not in cart"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):

        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            return self.add_to_favorites(user, recipe)
        elif request.method == 'DELETE':
            return self.remove_from_favorites(user, recipe)

    def add_to_favorites(self, user, recipe):

        serializer = FavoriteSerializer(data={'recipe': recipe}, context={'request': self.request, 'recipe': recipe})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Вернем детализированную информацию о рецепте
        response_serializer = RecipeSerializer(recipe, context={'request': self.request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorites(self, user, recipe):
   
        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response({"status": "removed from favorites"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"status": "not in favorites"}, status=status.HTTP_400_BAD_REQUEST)
    

        @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            return self.add_to_favorites(user, recipe)
        elif request.method == 'DELETE':
            return self.remove_from_favorites(user, recipe)

    def add_to_favorites(self, user, recipe):
        
        serializer = FavoriteSerializer(data={'recipe': recipe.id}, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

    # Вернем детализированную информацию о рецепте
        response_serializer = RecipeSerializer(recipe, context={'request': self.request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorites(self, user, recipe):
       
        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response({"status": "removed from favorites"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"status": "not in favorites"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        favorite, created = Favorite.objects.get_or_create(user=user, recipe=recipe)
        
        if not created:
            return Response(
                {'error': 'Recipe is already in favorites.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = FavoriteSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Удаление из избранного
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unfavorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        
        if not favorite.exists():
            return Response(
                {'error': 'Recipe not found in favorites.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    """
        

class FavoriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # Добавление рецепта в избранное
    @action(detail=True, methods=['post'], url_path='favorite')
    def create(self, request, pk=None):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
        
        if not created:
            return Response(
                {'error': 'Recipe is already in favorites.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = FavoriteSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Удаление рецепта из избранного
    @action(detail=True, methods=['delete'], url_path='favorite')
    def destroy(self, request, pk=None):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        
        if not favorite.exists():
            return Response(
                {'error': 'Recipe not found in favorites.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination



"""

кусок из юзерского вьюсета 

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        user = request.user
        try:
            subscribed_to = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

        if user == subscribed_to:
            return Response({"detail": "Невозможно подписаться на самого себя."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Проверка на существующую подписку
        if Subscription.objects.filter(user=user, subscribed_to=subscribed_to).exists():
            return Response({"detail": "Вы уже подписаны на этого пользователя."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Создание подписки
        subscription = Subscription.objects.create(user=user, subscribed_to=subscribed_to)
        serializer = SubscriptionSerializer(subscription, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        if not Recipe.objects.filter(id=recipe_id).exists():
            return Response(
                {"detail": "Recipe not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        return super().create(request, *args, **kwargs)

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes_by_action = {
        "list": (AllowAny,),
        "retrieve": (AllowAny,),
        "create": (IsAuthenticated,),
        "update": (IsAuthorOrReadOnly,),
        "partial_update": (IsAuthorOrReadOnly,),
        "destroy": (IsAuthorOrReadOnly,),
    }
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('author', 'tags__slug')
    search_fields = ('^name',)
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None and user.is_authenticated:
            if is_favorited.lower() == 'true':
                queryset = queryset.filter(favorite__user=user)

        is_in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart is not None and user.is_authenticated:
            if is_in_shopping_cart.lower() == 'true':
                queryset = queryset.filter(shoppingcart__user=user)

        return queryset.distinct()

    def get_permissions(self):
        return [
            permission() for permission in self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        ]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def list(self, request, *args, **kwargs):
        
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        try:
            self.get_object()
        except Recipe.DoesNotExist:
            raise NotFound("Recipe not found.")
        
        self.action_model = Favorite
        self.action_add_status = "added to favorites"
        return self.perform_action(request, pk, add=True)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unfavorite(self, request, pk=None):
        self.action_model = Favorite
        self.action_remove_status = "removed from favorites"
        return self.perform_action(request, pk, add=False)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_cart(self, request, pk=None):
        self.action_model = ShoppingCart
        self.action_add_status = "added to cart"
        return self.perform_action(request, pk, add=True)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_from_cart(self, request, pk=None):
        self.action_model = ShoppingCart
        self.action_remove_status = "removed from cart"
        return self.perform_action(request, pk, add=False)
        """
