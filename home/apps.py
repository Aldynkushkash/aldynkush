from django.apps import AppConfig
from django.dispatch import Signal

from .utilities import send_activation_notification

user_registered = Signal(providing_args=['instance'])

class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
    verbose_name = 'Алдын кушкаш'

def user_registered_dispatcher(sender, **kwargs):
    send_activation_notification(kwargs['instance'])

user_registered.connect(user_registered_dispatcher)
