import csv
import os

from django.core.management.base import BaseCommand

from foodgram.models import Ingredient


class Command(BaseCommand):
    help = "Импорт данных из CSV-файла в модель Ingredient"

    def handle(self, *args, **kwargs):
        csv_file = "/app/data/ingredients.csv"

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"Файл {csv_file} не найден"))
            return

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
                try:
                    Ingredient.objects.create(
                        name=name, measurement_unit=measurement_unit
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Ингредиент {name} добавлен"
                    ))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Ошибка при добавлении {name}: {e}")
                    )

        self.stdout.write(self.style.SUCCESS("Импорт завершен!"))
