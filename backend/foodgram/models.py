from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_subscribed = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("username", "first_name", "last_name")

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='foodgram_users',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='foodgram_user_permissions',
        blank=True
    )


class Tag(models.Model):
    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=128, unique=True)
    measurement_unit = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    image = models.ImageField(upload_to="recipes/")
    description = models.TextField()
    ingredients = models.ManyToManyField(Ingredient, through="RecipeIngredient")
    tags = models.ManyToManyField(Tag)
    cooking_time = models.PositiveIntegerField()
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
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


class Favorite(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        db_table = "favorite"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="unique_favorite_recipe"
            )
        ]


class ShoppingCart(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        db_table = "shopping_cart"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="unique_shopping_cart_recipe"
            )
        ]
