# Проект Foodgram

Foodgram — это API для платформы, на которой пользователи могут публиковать рецепты, добавлять рецепты в избранное и корзину покупок, подписываться на любимых авторов, а также скачивать список покупок.

## Функционал

- **Аутентификация пользователей**: Регистрация, авторизация с использованием Djoser и токенов JWT.
- **Рецепты**: Пользователи могут создавать, просматривать, редактировать и удалять рецепты.
- **Избранное и корзина покупок**: Пользователи могут добавлять рецепты в избранное и в корзину для дальнейшего использования.
- **Подписки**: Возможность подписываться на других пользователей и просматривать рецепты авторов, на которых подписан пользователь.
- **Фильтрация и поиск**: Возможность фильтровать рецепты по тегам, искать ингредиенты.

## Эндпоинты API

### Аутентификация

- Получение токена: `/api/auth/token/login/` (POST)
- Удаление токена: `/api/auth/token/logout/` (POST)

### Пользователи

- Регистрация: `/api/users/` (POST)
- Список пользователей: `/api/users/` (GET)
- Информация о текущем пользователе: `/api/users/me/` (GET)
- Подписка на пользователя: `/api/users/{id}/subscribe/` (POST)
- Отписка от пользователя: `/api/users/{id}/subscribe/` (DELETE)

### Рецепты

- Список и создание рецептов: `/api/recipes/` (GET, POST)
- Детали рецепта: `/api/recipes/{recipe_id}/` (GET, PATCH, DELETE)
- Добавление рецепта в избранное: `/api/recipes/{recipe_id}/favorite/` (POST)
- Удаление рецепта из избранного: `/api/recipes/{recipe_id}/favorite/` (DELETE)
- Добавление рецепта в корзину покупок: `/api/recipes/{recipe_id}/shopping_cart/` (POST)
- Удаление рецепта из корзины покупок: `/api/recipes/{recipe_id}/shopping_cart/` (DELETE)
- Скачивание списка покупок: `/api/recipes/download_shopping_cart/` (GET)

### Ингредиенты и теги

- Список ингредиентов: `/api/ingredients/` (GET)
- Список тегов: `/api/tags/` (GET)

### Подписки и фильтры

- Список подписок пользователя: `/api/users/subscriptions/` (GET)
- Фильтрация рецептов по тегам: `/api/recipes/?tags={tag_slug}`

## Как запустить проект:

### Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/kateboosha/foodgram/
```

```
cd foodgram
```

### Cоздать и активировать виртуальное окружение:

```
python3 -m venv env
```

```
source env/bin/activate
```

### Установить зависимости из файла requirements.txt:

```
python3 -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

### Выполнить миграции:

```
python3 manage.py migrate
```

### Запустить проект:

```
python3 manage.py runserver
```

### Технологический стек
+ Python: 3.9
+ Django
+ Django REST Framework
+ SimpleJWT

### Автор 

Проект выполнила [Катя](https://github.com/kateboosha/) в рамках курса [Яндекс-Парктикума](https://github.com/yandex-praktikum/)