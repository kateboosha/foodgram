from rest_framework import serializers
from .models import User, Tag, Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'avatar')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'ingredient', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'description', 'ingredients', 'tags', 'cooking_time', 'is_favorited', 'is_in_shopping_cart')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'description', 'ingredients', 'tags', 'cooking_time')

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        if validated_data.get('image'):
            instance.image = validated_data.get('image')
        instance.save()
        instance.ingredients.clear()
        self._save_ingredients(instance, ingredients_data)
        instance.tags.set(tags_data)
        return instance

    def _save_ingredients(self, recipe, ingredients_data):
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeMinifiedSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'recipe')


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeMinifiedSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe')
