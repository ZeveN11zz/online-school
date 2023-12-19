from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse


# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=300, verbose_name='Категория', unique=True)
    slug = models.SlugField(db_index=True, max_length=50, unique=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['name']
        verbose_name = 'Категория товаров'
        verbose_name_plural = 'Категории товаров'


class ProductProperty(models.Model):
    name = models.CharField(max_length=200, verbose_name='Наименование', unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Характеристика товара'
        verbose_name_plural = 'Характеристики товаров'


class Product(models.Model):
    name = models.CharField(max_length=300, verbose_name='Наименование')
    slug = models.SlugField(db_index=True, max_length=50, unique=True)
    category = models.ForeignKey(Category, verbose_name='Категория товара', on_delete=models.RESTRICT)
    description = models.TextField(verbose_name='Описание', blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена', default=0)
    in_sale = models.BooleanField(default=False, verbose_name='В продаже')
    properties = models.ManyToManyField(ProductProperty, verbose_name='Характеристики', through='PropertyValue')

    def __str__(self):
        return f'{self.category.name}: {self.name}'

    def as_dict(self):
        return {
            'id': self.pk,
            'name': self.name,
            'category': self.category.name,
            'price': self.price,
            'in_sale': self.in_sale,
            'properties': [f'{_.property.name}: {_.value}' for _ in self.propertyvalue_set.all()]
        }

    def get_absolute_url(self):
        return reverse('product', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['pk']
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class PropertyValue(models.Model):
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    property = models.ForeignKey(ProductProperty, on_delete=models.RESTRICT, verbose_name='Характеристика')
    value = models.CharField(max_length=200, verbose_name='Значение')

    def as_dict(self):
        return {self.property.name: self.value}

    class Meta:
        ordering = ['property__name']
        unique_together = ('product', 'property')
        verbose_name = 'Характеристика товара'
        verbose_name_plural = 'Характеристики товара'


class Cart(models.Model):
    customer = models.OneToOneField(User, verbose_name='Покупатель', on_delete=models.RESTRICT)
    start_date = models.DateField(verbose_name='Время начала', auto_now=True)

    def __str__(self):
        return f'{self.customer.get_full_name()}: товаров'

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'


class CartContent(models.Model):
    cart = models.ForeignKey(Cart, verbose_name='Состав корзины', on_delete=models.RESTRICT)
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    def __str__(self):
        return f'{self.product}'

    def as_dict(self):
        return self.product.as_dict() | {'quantity': self.quantity}

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Order(models.Model):
    customer = models.ForeignKey(User, verbose_name='Покупатель', on_delete=models.RESTRICT)
    order_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата заказа')
    items = models.JSONField(verbose_name='Состав заказа', encoder=DjangoJSONEncoder)
    payment_date = models.DateTimeField(verbose_name='Дата оплаты')
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость заказа')

    def __str__(self):
        return (f'Заказ {self.pk} от {self.order_date.strftime("%d.%m.%Y %H:%M")}: {self.customer.get_full_name()}'
                f' на сумму {self.cost}')

    class Meta:
        ordering = ['-order_date']
        verbose_name = 'История заказов'
        verbose_name_plural = 'Истории заказов'


class DisputeChoice(models.Model):
    choice = models.CharField(max_length=50, verbose_name='Выбор', unique=True)

    def __str__(self):
        return self.choice

    class Meta:
        verbose_name = 'Решение по рекламации'
        verbose_name_plural = 'Решения по рекламациям'


class Dispute(models.Model):
    order = models.OneToOneField(Order, verbose_name='Заказ', on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    dispute_text = models.TextField(verbose_name='Суть претензии')
    decision = models.ForeignKey(DisputeChoice, verbose_name='Принятое решение', on_delete=models.RESTRICT,
                                 blank=True, null=True)
    decision_text = models.TextField(verbose_name='Суть решения', blank=True, null=True)
    decision_date = models.DateTimeField(verbose_name='Дата принятого решения', null=True)

    def __str__(self):
        return (f'Заказ {self.order.pk} от {self.order.order_date}, '
                f'Решение: {self.decision.choice if self.decision else "не принято"}')

    def get_absolute_url(self):
        return reverse('dispute_detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = 'Рекламация'
        verbose_name_plural = 'Рекламации'
        ordering = ['created_at']
