from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import User, Tag, Ingredient, Recipe, Favorite, ShoppingCart, RecipeIngredient
from .serializers import (
    UserSerializer, TagSerializer, IngredientSerializer, RecipeSerializer, 
    FavoriteSerializer,
)


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes_by_action = {
        'create': [AllowAny],
        'list': [IsAuthenticated],
        'me': [IsAuthenticated],
        'set_password': [IsAuthenticated],
    }

    def get_permissions(self):
        try:
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes_by_action = {
        'list': [AllowAny],
        'retrieve': [AllowAny],
        'create': [IsAuthenticated],
        'update': [IsAuthorOrReadOnly],
        'partial_update': [IsAuthorOrReadOnly],
        'destroy': [IsAuthorOrReadOnly],
    }

    def get_permissions(self):
        try:
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        Favorite.objects.create(user=request.user, recipe=recipe)
        return Response({'status': 'added to favorites'})

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unfavorite(self, request, pk=None):
        recipe = self.get_object()
        Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        return Response({'status': 'removed from favorites'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_cart(self, request, pk=None):
        recipe = self.get_object()
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        return Response({'status': 'added to cart'})

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_from_cart(self, request, pk=None):
        recipe = self.get_object()
        ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        return Response({'status': 'removed from cart'})


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_list(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)
        ingredients = {}

        recipe_ids = shopping_cart.values_list('recipe_id', flat=True)
        recipe_ingredients = RecipeIngredient.objects.filter(recipe_id__in=recipe_ids)

        for item in recipe_ingredients:
            name = item.ingredient.name
            measurement_unit = item.ingredient.measurement_unit
            amount = item.amount
            if name in ingredients:
                ingredients[name]['amount'] += amount
            else:
                ingredients[name] = {'amount': amount, 'measurement_unit': measurement_unit}


        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.pdf"'

        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        p.setFont("Helvetica", 12)
        y_position = height - 50

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, y_position, "Список покупок")
        p.setFont("Helvetica", 12)
        y_position -= 30

        for name, data in ingredients.items():
            ingredient_text = f"{name} ({data['measurement_unit']}) — {data['amount']}"
            p.drawString(100, y_position, ingredient_text)
            y_position -= 20

            if y_position < 50:
                p.showPage()
                p.setFont("Helvetica", 12)
                y_position = height - 50

        p.showPage()
        p.save()

        return response
