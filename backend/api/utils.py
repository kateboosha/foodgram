from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def generate_pdf(user, ingredients):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="shopping_cart_{user.username}.pdf"'
    )

    pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("DejaVuSans", 12)
    _, height = letter
    y = height - 40

    p.drawString(100, y, f"Список покупок для пользователя: {user.username}")
    y -= 20

    if not ingredients:
        p.drawString(100, y, "Список покупок пуст.")
        p.showPage()
        p.save()
        return response

    for ingredient in ingredients:
        p.drawString(
            100,
            y,
            f"{ingredient['ingredient__name']}: {ingredient['total_amount']} "
            f"{ingredient['ingredient__measurement_unit']}"
        )
        y -= 20
        if y < 40:
            p.showPage()
            p.setFont("DejaVuSans", 12)
            y = height - 40

    p.showPage()
    p.save()

    return response
