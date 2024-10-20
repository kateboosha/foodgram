import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from djoser.serializers import UserSerializer
from foodgram.models import (
    User,
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Subscription,
)


class Base64ImageField(serializers.ImageField):
    """Поле для обработки изображения, закодированного в Base64."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            # Извлечение данных формата изображения и содержимого
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name="temp." + ext)
        return super().to_internal_value(data)

    def to_representation(self, value):
        """Возвращает URL-ссылку на изображение."""
        if value:
            return value.url
        return None


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для обработки аватара в формате Base64."""
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class CustomUserSerializer(serializers.ModelSerializer):
    """Полноценный сериализатор для вьюсета пользователей."""
    password = serializers.CharField(write_only=True, min_length=8)
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "is_subscribed",
            "avatar",
        )
        extra_kwargs = {
            "email": {"max_length": 254},
            "username": {"max_length": 150},
            "first_name": {"max_length": 150},
            "last_name": {"max_length": 150},
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, subscribed_to=obj).exists()
        return False


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Отправляем в сеттинги для странички регистрации."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "password")

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = serializers.ListField(child=serializers.DictField(), write_only=True)
    tags = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    image = Base64ImageField()
    text = serializers.CharField(source='description')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "name",
            "image",
            "text",
            "ingredients",
            "tags",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Поле 'ingredients' не может быть пустым.")

        unique_ingredients = set()
        for ingredient in value:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')

        # Проверка на повторяющиеся ингредиенты
            if ingredient_id in unique_ingredients:
                raise serializers.ValidationError("Ингредиенты не должны повторяться.")
            unique_ingredients.add(ingredient_id)

        # Проверка существования ингредиента
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(f"Ингредиент с id {ingredient_id} не существует.")

        # Преобразуем значение amount в int для корректной проверки
            try:
                amount = int(amount)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Количество ингредиента должно быть числом.")

            if amount < 1:
                raise serializers.ValidationError("Количество ингредиента должно быть больше 0.")

        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Поле 'tags' не может быть пустым.")
        unique_tags = set(value)
        if len(unique_tags) != len(value):
            raise serializers.ValidationError("Теги не должны повторяться.")
        for tag_id in value:
            if not Tag.objects.filter(id=tag_id).exists():
                raise serializers.ValidationError(f"Тег с id {tag_id} не существует.")
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Время приготовления должно быть не менее 1 минуты.")
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        validated_data["author"] = self.context["request"].user
        recipe = Recipe.objects.create(**validated_data)

        self._save_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        tags_data = validated_data.pop("tags", None)

        if ingredients_data is None:
            raise serializers.ValidationError({"ingredients": "Поле 'ingredients' обязательно для обновления."})
        if tags_data is None:
            raise serializers.ValidationError({"tags": "Поле 'tags' обязательно для обновления."})

        if ingredients_data:
            instance.recipe_ingredients.all().delete()
            self._save_ingredients(instance, ingredients_data)

        if tags_data:
            instance.tags.set(tags_data)

        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.cooking_time = validated_data.get("cooking_time", instance.cooking_time)
        
        if validated_data.get("image"):
            instance.image = validated_data["image"]
        
        instance.save()
        return instance

    def _save_ingredients(self, recipe, ingredients_data):
        for ingredient in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient["id"],
                amount=ingredient["amount"]
            )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['ingredients'] = RecipeIngredientSerializer(
            instance.recipe_ingredients.all(), many=True).data
        representation['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return representation

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and ShoppingCart.objects.filter(user=user, recipe=obj).exists()

class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецептов с минимальным набором полей."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

class FavoriteSerializer(serializers.ModelSerializer):
    # Используем вложенный сериализатор для рецепта
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("recipe",)

    def validate(self, data):
        user = self.context["request"].user
        recipe = self.context.get("recipe")  # Получаем рецепт из контекста, переданного из ViewSet
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError("This recipe is already in favorites.")
        data["recipe"] = recipe  # Добавляем объект рецепта в данные для дальнейшего использования
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        recipe = validated_data["recipe"]
        return Favorite.objects.create(user=user, recipe=recipe)


class ShoppingCartRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецепта при добавлении в корзину."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')  


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ("id", "recipe")


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count', read_only=True)
    avatar = Base64ImageField()

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
        # Ограничиваем количество рецептов с помощью параметра recipes_limit
        recipes_limit = self.context['request'].query_params.get('recipes_limit')
        if recipes_limit is not None:
            recipes = obj.recipes.all()[:int(recipes_limit)]
        else:
            recipes = obj.recipes.all()
        return RecipeSerializer(recipes, many=True, context=self.context).data


"""
   
class SubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='subscribed_to.email')
    id = serializers.IntegerField(source='subscribed_to.id')
    username = serializers.CharField(source='subscribed_to.username')
    first_name = serializers.CharField(source='subscribed_to.first_name')
    last_name = serializers.CharField(source='subscribed_to.last_name')
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(source='subscribed_to.avatar', required=False, allow_null=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return Subscription.objects.filter(user=user, subscribed_to=obj.subscribed_to).exists()

    def get_recipes(self, obj):
        recipes_limit = self.context['request'].query_params.get('recipes_limit')
        queryset = obj.subscribed_to.recipes.all()
        if recipes_limit:
            queryset = queryset[:int(recipes_limit)]
        return RecipeSerializer(queryset, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.subscribed_to.recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    subscribed_to = CustomUserSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'subscribed_to', 'created_at')
        
class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("user", "recipe")

    def validate(self, data):
        user = self.context["request"].user
        recipe = data["recipe"]
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError("This recipe is already in favorites.")
        return data



        class CustomUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, min_length=8)
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "is_subscribed",
            "avatar",
        )
        extra_kwargs = {
            "email": {"max_length": 254},
            "username": {"max_length": 150},
            "first_name": {"max_length": 150},
            "last_name": {"max_length": 150},
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.is_subscribed
        return False
"""