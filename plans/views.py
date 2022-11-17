from django.shortcuts import render, get_object_or_404, redirect
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from .models import FitnessPlan, Customer1
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
import stripe

stripe.api_key = "sk_test_51KyBUjIBWo2GmTUWpsnFhvgPx2s84A59vBl3AQIkxHE7EjaW0" \
                 "j6vg7bRsz0gJaY4NbPaBK1NxHFqQo692gpxVoCr00j1N9hNZC "


def home(request):
    plans = FitnessPlan.objects
    return render(request, 'plans/home.html', {'plans': plans})


def plan(request, pk):
    plan = get_object_or_404(FitnessPlan, pk=pk)
    if plan.premium:
        if request.user.is_authenticated:
            try:
                if request.user.customer1.membership:
                    return render(request, 'plans/plan.html', {'plan': plan})
            except Customer1.DoesNotExist:
                return redirect('join')
        return redirect('join')
    else:
        return render(request, 'plans/plan.html', {'plan': plan})


def join(request):
    return render(request, 'plans/join.html')


@login_required
def checkout(request):
    try:
        if request.user.customer1.membership:
            return redirect("settings")
    except Customer1.DoesNotExist:
        pass

    coupons = {"halloween": 31, "welcome": 10}
    if request.method == "POST":
        stripe_customer = stripe.Customer.create(email=request.user.email, source=request.POST["stripeToken"])
        plan = "price_1M4f6KIBWo2GmTUW6bdFj4mO"
        if request.POST["plan"] == "yearly":
            plan = "price_1M4f7LIBWo2GmTUWZ3hDsIAT"
        if request.POST["coupon"] in coupons:
            coupon_from_user = request.POST["coupon"].lower()
            percentage = coupons[coupon_from_user]
            try:
                coupon = stripe.Coupon.create(duration="once", id=coupon_from_user, percent_off=percentage)
            except:
                pass
            subscription = stripe.Subscription.create(customer=stripe_customer.id, items=[{"plan": plan}],
                                                      coupon=coupon_from_user)
        else:
            subscription = stripe.Subscription.create(customer=stripe_customer.id, items=[{"plan": plan}])

        customer = Customer1()
        customer.user = request.user
        customer.stripe_id = stripe_customer.id
        customer.membership = True
        customer.cancel_at_period_end = False
        customer.stripe_subscription_id = subscription.id
        customer.save()

        return redirect("home")
    else:
        plan, coupon = "monthly", "none"
        price, og_dollar, coupon_dollar, final_dollar = 1000, 10, 0, 10
        if request.method == "GET" and "plan" in request.GET:
            if request.GET["plan"] == "yearly":
                plan, price, og_dollar, final_dollar = "yearly", 10000, 100, 100
        if request.method == "GET" and "coupon" in request.GET:
            if request.GET["coupon"].lower() in coupons:
                coupon = request.GET["coupon"].lower()
                percentage = coupons[coupon]
                coupon_price = int((percentage / 100) * price)
                price = price - coupon_price
                coupon_dollar = str(coupon_price)[:-2] + "." + str(coupon_price)[-2:]
                final_dollar = str(price)[:-2] + "." + str(price)[-2:]
        return render(request, 'plans/checkout.html', {"plan": plan, "coupon": coupon, "price": price,
                                                       "og_dollar": og_dollar, "coupon_dollar": coupon_dollar,
                                                       "final_dollar": final_dollar})


def settings(request):
    membership, cancel_at_period_end = False, False
    if request.method == "POST":
        pass
    else:
        try:
            if request.user.customer1.membership:
                membership = True
            if request.user.customer1.cancel_at_period_end:
                cancel_at_period_end = True
        except Customer1.DoesNotExist:
            membership = False
    return render(request, 'registration/settings.html', {"membership": membership,
                                                          "cancel_at_period_end": cancel_at_period_end})


class SignUp(generic.CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid
