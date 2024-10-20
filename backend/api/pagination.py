from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Пагинатор с 'limit'."""
    page_size_query_param = 'limit'
