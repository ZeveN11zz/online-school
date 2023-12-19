from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import html_safe
from django.utils.safestring import SafeString
from django.utils.translation import ngettext

from shop.models import *


# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['name']}


@admin.register(ProductProperty)
class ProductPropertyAdmin(admin.ModelAdmin):
    pass


class PropertyValueAdmin(admin.TabularInline):
    model = PropertyValue
    extra = 0
    min_num = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [PropertyValueAdmin]
    prepopulated_fields = {'slug': ['name']}
    search_fields = ['name']
    list_display = ['category', 'name', 'price', 'in_sale']
    list_filter = ['category', 'in_sale']
    list_editable = ['price', 'in_sale']
    save_as = True
    actions = ['sale_products', 'withdraw_products']

    @admin.action(description="Снять с продажи")
    def withdraw_products(self, request, queryset):
        updated = queryset.update(in_sale=False)
        self.message_user(
            request,
            ngettext(
                "%d товар снят с продажи.",
                "%d товаров снято с продажи.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description="Выложить в продажу")
    def sale_products(self, request, queryset):
        updated = queryset.update(in_sale=True)
        self.message_user(
            request,
            ngettext(
                "%d товар выставлен на продажу.",
                "%d товаров выставлено на продажу.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )


class CartContentAdmin(admin.TabularInline):
    model = CartContent
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartContentAdmin]

    def has_add_permission(self, request):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    search_fields = ['cost', 'customer__username', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['order_date', 'cost', 'payment_date', 'customer', 'pretty_items']
    list_display = ['order_date', 'cost']
    fieldsets = [
        (
            None,
            {
                "fields": ["order_date", "cost", "payment_date", "customer"],
            },
        ),
        (
            "Состав заказа",
            {
                "classes": ["collapse"],
                "fields": ["pretty_items"],
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    @admin.display()
    def pretty_items(self, obj):
        result = []
        for item in obj.items:
            properties = item['properties']
            result.append(
                f'{item["category"]}: {item["name"]} ({", ".join(properties)}), '
                f'Цена: {item["price"]}, Кол-во: {item["quantity"]}'
            )
        return SafeString('<pre>{}</pre>'.format('\n'.join(result)))

    pretty_items.short_description = 'Состав заказа'


@admin.register(DisputeChoice)
class DisputeChoiceAdmin(admin.ModelAdmin):
    pass


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    readonly_fields = ['order', 'created_at', 'decision_date', 'dispute_text']
    list_filter = ['decision']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_form(self, request, form, change):
        if 'decision' in form.changed_data:
            if form.cleaned_data['decision']:
                form.instance.decision_date = timezone.now()
            else:
                form.instance.decision_date = None
        return super().save_form(request, form, change)
