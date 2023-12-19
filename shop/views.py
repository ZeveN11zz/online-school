from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView, LoginView
from django.core.serializers import serialize
from django.db.models import F, Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView, UpdateView, CreateView

from shop.forms import RegisterForm, DisputeForm
from shop.models import *


# Create your views here.


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm

    def get_success_url(self):
        return reverse('index')

    def form_valid(self, form):
        result = super().form_valid(form)
        # new_user = authenticate(
        #     self.request, username=form.cleaned_data['email'], password=form.cleaned_data['password1'])
        # login(self.request, new_user)
        login(self.request, self.object)
        return result


class IndexView(ListView):
    model = Product
    paginate_by = 6

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.kwargs.get('pk')
        if category:
            queryset = queryset.filter(category=category)
        return queryset.filter(in_sale=True).distinct()


class CatalogueView(ListView):
    model = Category
    paginate_by = 6


class ProductListView(ListView):
    model = Product
    paginate_by = 6

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.kwargs.get('slug')
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset.filter(in_sale=True).distinct()


class ProductDetailView(DetailView):
    model = Product


class CategoryListView(ListView):
    model = Category
    paginate_by = 6


class CartView(LoginRequiredMixin, TemplateView):
    model = Cart
    template_name = 'shop/cart_list.html'

    def get_object(self):
        return self.model.objects.get(customer=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['object'] = obj
        context['total'] = obj.cartcontent_set.aggregate(total=Sum(F('quantity')*F('product__price')))['total']
        return context

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.cartcontent_set.filter(product__slug=kwargs['slug']).update(quantity=request.POST.get('quantity', 0))
        obj.cartcontent_set.filter(quantity=0).delete()
        return HttpResponseRedirect(redirect_to=request.META.get('HTTP_REFERER'))


class EditCartView(LoginRequiredMixin, UpdateView):
    def post(self, request, *args, **kwargs):
        product = Product.objects.get(slug=kwargs['slug'])
        cart, _ = Cart.objects.get_or_create(customer=self.request.user)
        submit = request.POST.get('submit')
        if submit == 'add':
            cart_content, _ = cart.cartcontent_set.get_or_create(product=product, defaults={'quantity': 0})
            cart_content.quantity += 1
            cart_content.save()
        if submit == 'update':
            cart_content, _ = cart.cartcontent_set.get_or_create(product=product, defaults={'quantity': 0})
            cart_content.quantity = int(request.POST.get('quantity', 0))
            cart_content.save()
        elif submit == 'remove':
            cart.cartcontent_set.filter(product=product).delete()
        if not cart.cartcontent_set.count():
            cart.delete()
        return HttpResponseRedirect(redirect_to=reverse('cart'))


class PaymentView(LoginRequiredMixin, TemplateView):
    model = Order
    template_name = 'shop/payment_success.html'

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        from django.template.response import TemplateResponse
        return TemplateResponse(self.request, self.template_name)

    def post(self, request, *args, **kwargs):
        cart = Cart.objects.get(customer=request.user)
        cost = cart.cartcontent_set.aggregate(total=Sum(F('quantity')*F('product__price')))['total']
        content_dict = []
        for cart_content in cart.cartcontent_set.iterator():
            content_dict.append(cart_content.as_dict())
        Order.objects.create(
            customer=cart.customer, items=content_dict, payment_date=timezone.now(),
            order_date=cart.start_date, cost=cost)
        cart.delete()
        return HttpResponseRedirect(reverse('orders'))


class OrdersView(LoginRequiredMixin, ListView):
    model = Order

    def get_queryset(self):
        return super().get_queryset().filter(customer=self.request.user)


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order

    def get_queryset(self):
        return super().get_queryset().filter(customer=self.request.user)


class ReclamationView(LoginRequiredMixin, ListView):
    model = Order
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(order__customer=self.request.user)


class DisputeCreateView(LoginRequiredMixin, CreateView):
    model = Dispute
    form_class = DisputeForm

    def get_initial(self):
        initials = super().get_initial()
        initials['order'] = Order.objects.get(pk=self.kwargs['order'], customer=self.request.user)
        return initials

    def get_success_url(self):
        return reverse('order', kwargs={'pk': self.kwargs['order']})


class DisputeUpdateView(LoginRequiredMixin, UpdateView):
    model = Dispute
    form_class = DisputeForm

    def get_queryset(self):
        return super().get_queryset().filter(order__customer=self.request.user)


class DisputeDetailView(LoginRequiredMixin, DetailView):
    model = Dispute

    def get_queryset(self):
        return super().get_queryset().filter(order__customer=self.request.user)
