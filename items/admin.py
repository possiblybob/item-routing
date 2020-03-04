from django.contrib import admin

from items.models import Item, Transaction


class TransactionInlineAdmin(admin.TabularInline):
    """inline administration of Transactions"""
    model = Transaction
    extra = 1
    show_change_link = True


class ItemAdmin(admin.ModelAdmin):
    """administration for Item objects"""
    inlines = [
        TransactionInlineAdmin,
    ]


admin.site.register(Item, ItemAdmin)
admin.site.register(Transaction)