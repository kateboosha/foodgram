from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


EMAIL_MAX_LENGTH = 254
USERNAME_MAX_LENGTH = 150
FIRST_NAME_MAX_LENGTH = 150
LAST_NAME_MAX_LENGTH = 150
TAG_NAME_MAX_LENGTH = 32
TAG_SLUG_MAX_LENGTH = 32
INGREDIENT_NAME_MAX_LENGTH = 128
MEASUREMENT_UNIT_MAX_LENGTH = 64
RECIPE_NAME_MAX_LENGTH = 256


class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=EMAIL_MAX_LENGTH)
    username = models.CharField(
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=(
                    'Username может содержать только цифры,'
                    'буквы и @/./+/-/_ .'
                ),
                code='invalid_username'
            )
        ]
    )
    first_name = models.CharField(max_length=FIRST_NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=LAST_NAME_MAX_LENGTH)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_subscribed = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("username", "first_name", "last_name")


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    subscribed_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscribed_to'],
                name='unique_subscription'
            )
        ]


class Tag(models.Model):
    name = models.CharField(max_length=TAG_NAME_MAX_LENGTH, unique=True)
    slug = models.SlugField(max_length=TAG_SLUG_MAX_LENGTH, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=INGREDIENT_NAME_MAX_LENGTH, unique=True)
    measurement_unit = models.CharField(max_length=MEASUREMENT_UNIT_MAX_LENGTH)

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=RECIPE_NAME_MAX_LENGTH)
    image = models.ImageField(upload_to="recipes/")
    description = models.TextField()
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name='recipes'
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    cooking_time = models.PositiveIntegerField()
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='ingredient_recipes',
        on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="unique_recipe_ingredient"
            )
        ]


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="unique_user_recipe_relation"
            )
        ]


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorites"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f'{self.user.email} добавил {self.recipe.name} в избранное'


class ShoppingCart(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        db_table = "shopping_cart"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="unique_shopping_cart_recipe"
            )
        ]
