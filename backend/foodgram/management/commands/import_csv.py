import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from foodgram.models import Ingredient


class Command(BaseCommand):
    help = "Импорт данных из CSV-файла в модель Ingredient"

    def handle(self, *args, **kwargs):
        csv_file = os.path.join(settings.BASE_DIR, "data", "ingredients.csv")

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"Файл {csv_file} не найден"))
            return

        ingredients = []

        with open(csv_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            for row in reader:
                if len(row) != 2:
                    self.stdout.write(
                        self.style.ERROR(f"Неверный формат строки: {row}")
                    )
                    continue

                name, measurement_unit = row
                ingredients.append(Ingredient(
                    name=name,
                    measurement_unit=measurement_unit
                ))

        try:
            Ingredient.objects.bulk_create(ingredients)
            self.stdout.write(self.style.SUCCESS("Импорт завершен!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при импорте: {e}"))
