from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Sum
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
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


class ProductListView(ListView):
    model = Product
    paginate_by = 6

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(in_sale=True).distinct()


class ProductDetailView(DetailView):
    model = Product


class CartView(LoginRequiredMixin, TemplateView):
    model = Cart
    template_name = 'shop/cart_list.html'

    def get_object(self):
        return self.model.objects.get(customer=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['object'] = obj
        context['total'] = obj.cartcontent_set.aggregate(total=Sum(F('product__price')))['total']
        return context

    def post(self, request, *args, **kwargs):
        return HttpResponseRedirect(redirect_to=request.META.get('HTTP_REFERER'))


class EditCartView(LoginRequiredMixin, UpdateView):
    def post(self, request, *args, **kwargs):
        product = Product.objects.get(slug=kwargs['slug'])
        cart, _ = Cart.objects.get_or_create(customer=self.request.user)
        submit = request.POST.get('submit')
        if submit == 'add':
            cart_content, _ = cart.cartcontent_set.get_or_create(product=product)
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
        cost = cart.cartcontent_set.aggregate(total=Sum(F('product__price')))['total']
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

    def form_valid(self, form):
        form.instance.order = Order.objects.get(pk=self.kwargs['order'], customer=self.request.user)
        return super().form_valid(form)

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


class LogoutView(LoginRequiredMixin, TemplateView):
    template_name = 'logout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = '?next=' + self.request.META.get('HTTP_REFERER')
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('logout'):
            logout(self.request)
            if not request.GET.get('next'):
                return HttpResponseRedirect(reverse('index'))
        return HttpResponseRedirect(request.GET.get('next'))


class ScheduleList(ListView):
    model = Schedule

    def get_queryset(self):
        return super().get_queryset().filter(assigned_to__isnull=True, date__gte=timezone.now().date())

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        if self.request.user.is_authenticated:
            context['active_bookings'] = self.model.objects.filter(
                date__gte=timezone.now().date(),
                assigned_to=self.request.user
            )
        return context


class ScheduleBookingView(LoginRequiredMixin, TemplateView):
    template_name = 'schedule_confirmation.html'
    success_template_name = 'schedule_booking_success.html'

    def get_object(self) -> Schedule | None:
        return get_object_or_404(
            Schedule,
            pk=self.kwargs['pk'],
            assigned_to__isnull=True,
            date__gte=timezone.now().date()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedule = self.get_object()
        context['schedule'] = schedule
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if request.POST.get('booking'):
            if context['schedule']:
                context['schedule'].assigned_to = self.request.user
                context['schedule'].save()
                return HttpResponse(
                    render(
                        request=request, template_name=self.success_template_name, context=context
                    )
                )
        return HttpResponseRedirect(reverse('schedule_booking', kwargs={'pk': self.kwargs['pk']}))
