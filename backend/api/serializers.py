from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from foodgram.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                             ShoppingCart, Subscription, Tag)

from .fields import Base64ImageField

User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для обработки аватара в формате Base64."""

    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, data):
        if 'avatar' not in data:
            raise serializers.ValidationError(
                {'avatar': 'Это поле обязательно.'}
            )
        return data


class UserDetailSerializer(serializers.ModelSerializer):
    """Полноценный сериализатор для вьюсета пользователей."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        return (
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and Subscription.objects.filter(
                user=self.context['request'].user,
                subscribed_to=obj
            ).exists()
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserDetailSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'name',
            'image',
            'ingredients',
            'tags',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
            'text',
        )

    def get_is_favorited(self, obj):
        return (
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and Favorite.objects.filter(
                user=self.context['request'].user,
                recipe=obj
            ).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return (
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and ShoppingCart.objects.filter(
                user=self.context['request'].user,
                recipe=obj
            ).exists()
        )


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):

    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'name',
            'image',
            'ingredients',
            'tags',
            'cooking_time',
            'text',
        )

    def validate(self, data):

        if 'ingredients' not in data or not data['ingredients']:
            raise serializers.ValidationError(
                {'ingredients': 'Поле "ingredients" не может быть пустым.'}
            )

        if 'tags' not in data or not data['tags']:
            raise serializers.ValidationError(
                {'tags': 'Поле "tags" не может быть пустым.'}
            )

        if 'text' not in data or not data['text']:
            raise serializers.ValidationError(
                {'text': 'Поле "text" не может быть пустым.'}
            )
        return data

    def validate_ingredients(self, value):
        unique_ingredients = set()
        for ingredient in value:
            ingredient_id = ingredient.get('id')
            if ingredient_id in unique_ingredients:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться.'
                )
            unique_ingredients.add(ingredient_id)
        return value

    def validate_tags(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError(
                'Теги не должны повторяться.'
            )
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле "image" не может быть пустым.'
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = user
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        RecipeIngredient.objects.filter(recipe=instance).clear()
        self._save_ingredients(instance, ingredients_data)
        instance.tags.set(tags_data, clear=True)

        return super().update(instance, validated_data)

    @staticmethod
    def _save_ingredients(recipe, ingredients_data):
        ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients)

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(instance, context=self.context)
        return serializer.data


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Вы уже добавили этот рецепт в избранное.'
            )
        ]

    def to_representation(self, instance):
        from .serializers import ShortRecipeSerializer
        return ShortRecipeSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Этот рецепт уже добавлен в корзину.'
            )
        ]

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe, context=self.context
        ).data


class SubscriptionSerializer(UserDetailSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_recipes(self, obj):
        recipes_limit = (
            self.context['request'].query_params.get('recipes_limit')
        )
        recipes = (
            obj.recipes.all()[:int(recipes_limit)]
            if recipes_limit is not None
            else obj.recipes.all()
        )

        return ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data


class SubscriptionActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'subscribed_to')

    def validate(self, data):
        user = self.context['request'].user
        author = data['subscribed_to']

        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )

        if Subscription.objects.filter(
            user=user, subscribed_to=author
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.'
            )

        return data


"""
    def get_is_favorited(self, obj):
        request = self.context.get('request')

        Вот эту реализацию стоит забрать в сериализатор для чтения рецептов.
        return (request and request.user.is_authenticated
                and Favorite.objects.filter(
                    user=request.user, recipe=obj
                ).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and ShoppingCart.objects.filter(
                    user=request.user, recipe=obj
                ).exists())
"""
