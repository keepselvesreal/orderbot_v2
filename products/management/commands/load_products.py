from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Load product data from an image into the database'

    # def add_arguments(self, parser):
    #     parser.add_argument('image_path', type=str, help='Path to the product image')

    def handle(self, *args, **options):
        # image_path = options['image_path'] # add_arguments로 만들지 않은 key 입력 시 오류 발생하네
        # text = extract_text_from_image(image_path)
        # products = parse_product_info(text)
        products = [
            ('떡케익5호', 1, 54000),
            ('무지개 백설기 케익', 1, 51500),
            ('미니 백설기', 35, 31500),
            ('개별 모듬팩', 1, 13500)
            ]
        
        for product_name, quantity, price in products:
            product = Product(product_name=product_name, quantity=quantity, price=price)
            product.save()

        self.stdout.write(self.style.SUCCESS('Successfully loaded product data into the database.'))
