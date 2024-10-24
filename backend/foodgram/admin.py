from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)

admin.site.empty_value_display = "Не указано"


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "author",
        "cooking_time",
        "favorites_count",
        "shopping_cart_count",
    )
    list_editable = ("cooking_time",)
    search_fields = ("name", "author__username")
    list_filter = ("tags",)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='Число добавлений в избранное')
    def favorites_count(self, obj):
        return obj.favorite_set.count()

    @admin.display(description='Число добавлений в корзину')
    def shopping_cart_count(self, obj):
        return obj.shoppingcart_set.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "measurement_unit")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")


@admin.register(get_user_model())
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name")
    search_fields = ("username", "email")
