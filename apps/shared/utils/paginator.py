from typing import Any
from typing import Dict
from typing import List

from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db.models import QuerySet


class ServicePaginator:
    def __init__(self, default_page_size: int = 20, max_page_size: int = 100):
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size

    def paginate(self, queryset: QuerySet, page: int, page_size: int):
        page_size = self._get_safe_page_size(page_size)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            'items': list(page_obj),
            'meta': {
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        }

    def _get_safe_page_size(self, page_size: Any) -> int:
        value = self._parse_int(page_size, default=self.default_page_size)

        value = min(value, self.max_page_size)

        if value < 1:
            value = self.default_page_size

        return value

    @staticmethod
    def _parse_int(value, default: int):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
