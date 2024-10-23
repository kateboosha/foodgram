# Проект Foodgram

**Foodgram** — это API для платформы, на которой пользователи могут публиковать рецепты, добавлять рецепты в избранное и корзину покупок, подписываться на любимых авторов, а также скачивать список покупок.

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

## Как запустить проект

### 1. Клонировать репозиторий:

```
git clone https://github.com/kateboosha/foodgram-project
cd foodgram-project
```

### 2. Создать файл `.env` на основе примера `.env.example`:

```
cp .env.example .env
```

### 3. Создать и активировать виртуальное окружение:

```
python3 -m venv env
source env/bin/activate
```

### 4. Установить зависимости:

```
pip install -r requirements.txt
```

### 5. Выполнить миграции:

```
python3 manage.py migrate
```

### 6. Запустить проект:

```
python3 manage.py runserver
```

## Спецификация API

После локального запуска проекта спецификация API доступна по адресу: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)

## Технологический стек

- **Python 3.9**
- **Django 3.2**
- **Django REST Framework 3.12.4**
- **PostgreSQL**
- **Gunicorn**
- **Docker**
- **Nginx**

## Основные библиотеки:

- asgiref==3.8.1
- attrs==24.2.0
- certifi==2024.8.30
- cffi==1.17.1
- chardet==5.2.0
- coreapi==2.3.3
- cryptography==43.0.1
- django-filter==2.4.0
- django-templated-mail==1.1.1
- djangorestframework-simplejwt==4.7.2
- djoser==2.0.3
- gunicorn==20.1.0
- psycopg2-binary==2.9.3
- pytest==6.2.4
- requests==2.32.3
- reportlab==4.2.5
- social-auth-app-django==3.1.0

## Автор

Проект выполнен [kateboosha](https://github.com/kateboosha) в рамках дипломной работы.