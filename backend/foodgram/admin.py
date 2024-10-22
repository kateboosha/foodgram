from django.contrib import admin
from .models import (
    User,
    Recipe,
    Ingredient,
    Tag,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
)


admin.site.empty_value_display = "Не указано"


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "author",
        "cooking_time",
        "is_favorited",
        "is_in_shopping_cart",
    )
    list_editable = ("cooking_time",)
    search_fields = ("name", "author__username")
    list_filter = ("tags", "is_favorited")
    inlines = (RecipeIngredientInline,)


class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "measurement_unit")


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")


class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name")
    search_fields = ("username", "email")


admin.site.register(User, UserAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
