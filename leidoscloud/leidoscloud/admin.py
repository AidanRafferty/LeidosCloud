from django.contrib import admin
from leidoscloud.models import *


class TransitionAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Transition._meta.get_fields()]


admin.site.register(Transition, TransitionAdmin)
admin.site.register(Key)
admin.site.register(API)
admin.site.register(StockData)
admin.site.register(Prediction)
