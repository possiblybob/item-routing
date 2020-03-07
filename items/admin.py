from django.contrib import admin

from items.models import Item, Transaction


class TransactionInlineAdmin(admin.TabularInline):
    """inline administration of Transactions"""
    model = Transaction
    extra = 1
    show_change_link = True
    readonly_fields = ('status', 'location', 'is_active',)


class ItemAdmin(admin.ModelAdmin):
    """administration for Item objects"""
    inlines = [
        TransactionInlineAdmin,
    ]
    list_display = ('id', 'amount',)
    readonly_fields = ('transaction', 'state',)


class TransactionAdmin(admin.ModelAdmin):
    """administration for Transaction objects"""
    readonly_fields = ('status', 'location', 'item', 'is_active',)
    list_display = ('id', 'status', 'location', 'item')
    list_filter = ('is_active',)
    list_select_related = ('item',)


admin.site.register(Item, ItemAdmin)
admin.site.register(Transaction, TransactionAdmin)
