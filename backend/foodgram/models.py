from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils.crypto import get_random_string

from .constants import (EMAIL_MAX_LENGTH, FIRST_NAME_MAX_LENGTH,
                        INGREDIENT_NAME_MAX_LENGTH, LAST_NAME_MAX_LENGTH,
                        MEASUREMENT_UNIT_MAX_LENGTH, RECIPE_NAME_MAX_LENGTH,
                        TAG_NAME_MAX_LENGTH, TAG_SLUG_MAX_LENGTH,
                        USERNAME_MAX_LENGTH)


class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=EMAIL_MAX_LENGTH)
    username = models.CharField(
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[AbstractUser.username_validator],
    )
    first_name = models.CharField(max_length=FIRST_NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=LAST_NAME_MAX_LENGTH)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        ordering = ('username',)


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions'
    )
    subscribed_to = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscribers'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscribed_to'],
                name='unique_subscription'
            ),
            models.CheckConstraint(
                check=~Q(user=F('subscribed_to')),
                name='prevent_self_subscription'
            ),
        ]
        ordering = ('user',)


class Tag(models.Model):
    name = models.CharField(max_length=TAG_NAME_MAX_LENGTH, unique=True)
    slug = models.SlugField(max_length=TAG_SLUG_MAX_LENGTH, unique=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LENGTH,
    )
    measurement_unit = models.CharField(max_length=MEASUREMENT_UNIT_MAX_LENGTH)

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_name_unit'
            )
        ]
        ordering = ('name',)


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=RECIPE_NAME_MAX_LENGTH)
    image = models.ImageField(upload_to='recipes/')
    text = models.TextField()
    ingredients = models.ManyToManyField(
        Ingredient, through='RecipeIngredient', related_name='recipes'
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    short_link_hash = models.CharField(max_length=6, unique=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    def generate_short_link(self):
        while True:
            short_link = get_random_string(6)
            if not Recipe.objects.filter(short_link_hash=short_link).exists():
                return short_link

    def save(self, *args, **kwargs):
        if not self.short_link_hash:
            self.short_link_hash = self.generate_short_link()
        super().save(*args, **kwargs)
