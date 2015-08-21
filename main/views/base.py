__author__ = 'cristian'

from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic.edit import View
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import views

__all__ = ["AdvisorView", "ClientView", "AdminView"]


def advisor_member_required(view_func, redirect_field_name=REDIRECT_FIELD_NAME, login_url='advisor:login'):
    """
    Decorator for views that checks that the user is logged in and is an advisor
    member, displaying the login page if necessary.
    """
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )(view_func)


def client_member_required(view_func, redirect_field_name=REDIRECT_FIELD_NAME, login_url='client:login'):
    """
    Decorator for views that checks that the user is logged in and is an advisor
    member, displaying the login page if necessary.
    """
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )(view_func)


class AdvisorView(View):
    @method_decorator(advisor_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super(AdvisorView, self).dispatch(request, *args, **kwargs)


class ClientView(View):
    @method_decorator(client_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super(ClientView, self).dispatch(request, *args, **kwargs)


class AdminView(View):
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super(AdminView, self).dispatch(request, *args, **kwargs)
