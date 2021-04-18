from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models.signals import post_save

from .utilities import get_timestamp_path, send_new_comment_notification


class AdvUser(AbstractUser):
    is_activated = models.BooleanField(default=True, db_index=True, verbose_name='Прошел активацию?')
    send_messages = models.BooleanField(default=True, verbose_name='Слать оповещения о новых комментариях?')
    
    def delete(self, *args, **kwargs):
        for ak in self.ak_set.all():
            ak.delete()
        super(AdvUser, self).delete(*args, **kwargs)

    class Meta(AbstractUser.Meta):
        pass

class Rubric(models.Model):
    name = models.CharField(max_length=20, db_index=True, unique=True, verbose_name='Название')
    order = models.SmallIntegerField(default=0, db_index=True, verbose_name='Порядок')
    super_rubric = models.ForeignKey('SuperRubric', on_delete=models.PROTECT, null=True, blank=True,
                                     verbose_name='Надрубрика')

class SuperRubricManager(models.Manager):
    def get_queryset(self):
        return super(SuperRubricManager, self).get_queryset().filter(super_rubric__isnull=True)

class SuperRubric(Rubric):
    objects = SuperRubricManager()

    def __str__(self):
        return self.name

    class Meta:
        proxy = True
        ordering = ('order', 'name')
        verbose_name = 'Надрубрика'
        verbose_name_plural = 'Надрубрики'

class SubRubricManager(models.Manager):
    def get_queryset(self):
        return super(SubRubricManager, self).get_queryset().filter(super_rubric__isnull=False)

class SubRubric(Rubric):
    objects = SubRubricManager()

    def __str__(self):
        return '%s - %s' % (self.super_rubric.name, self.name)

    class Meta:
        proxy = True
        ordering = ('super_rubric__order', 'super_rubric__name', 'order', 'name')
        verbose_name = 'Рубрика'
        verbose_name_plural = 'Рубрики'

class AK(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    rubric = models.ForeignKey(SubRubric, on_delete=models.PROTECT, verbose_name='Рубрика')
    title = models.CharField(max_length=250, verbose_name='Заголовок')
    slug = models.SlugField(max_length=250, unique_for_date='publish')
    author = models.ForeignKey(AdvUser, on_delete=models.CASCADE, verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    image = models.ImageField(blank=True, upload_to=get_timestamp_path, verbose_name='Изображение')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Выводить в списке?')
    publish = models.DateTimeField(default=timezone.now())
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    def delete(self, *args, **kwargs):
        for ai in self.additionalimage_set.all():
            ai.delete()
        super(AK, self).delete(*args, **kwargs)
    
    class Meta:
        ordering = ('-publish',)

    def __str__(self):
        return self.title

class AdditionalImage(models.Model):
    ak = models.ForeignKey(AK, on_delete=models.CASCADE, verbose_name='Запись')
    image = models.ImageField(upload_to=get_timestamp_path, verbose_name='Изображение')

    class Meta:
        verbose_name = 'Дополнительная иллюстрация'
        verbose_name_plural = 'Дополнительные иллюстрации'

class Comment(models.Model):
    ak = models.ForeignKey(AK, on_delete=models.CASCADE, verbose_name='Запись')
    author = models.CharField(max_length=30, verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Выводить на экран?')
    created = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Опубликован')

    class Meta:
        ordering = ['created']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

def post_save_dispatcher(sender, **kwargs):
    author = kwargs['instance'].ak.author
    if kwargs['created'] and author.send_messages:
        send_new_comment_notification(kwargs['instance'])

post_save.connect(post_save_dispatcher, sender=Comment)

