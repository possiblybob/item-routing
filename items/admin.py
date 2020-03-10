from django.contrib import admin
from django_object_actions import DjangoObjectActions


from items.models import Item, Transaction, TransactionStatus


class TransactionInlineAdmin(admin.TabularInline):
    """inline administration of Transactions"""
    model = Transaction
    extra = 1
    show_change_link = True
    readonly_fields = ('status', 'location', 'is_active',)


class ItemAdmin(DjangoObjectActions, admin.ModelAdmin):
    """administration for Item objects"""
    inlines = [
        TransactionInlineAdmin,
    ]
    list_display = ('id', 'amount',)
    readonly_fields = ('transaction', 'state',)

    def begin_refund(self, request, obj):
        """begins a new Transaction to initiate a refund for this Item"""
        obj.begin_refund()

    begin_refund.label = "Refund"
    begin_refund.short_description = "Begin a refund of this Item"

    change_actions = ('begin_refund',)

    def get_change_actions(self, request, object_id, form_url):
        """conditionally adds actions to Item based on status"""
        actions = super(ItemAdmin, self).get_change_actions(request, object_id, form_url)
        actions = list(actions)

        item = self.model.objects.get(pk=object_id)
        if item.status != TransactionStatus.ERROR:
            # only show refund action if Item is errored
            actions.remove('begin_refund')

        return actions


class TransactionAdmin(admin.ModelAdmin):
    """administration for Transaction objects"""
    readonly_fields = ('status', 'location', 'item', 'is_active',)
    list_display = ('id', 'status', 'location', 'item')
    list_filter = ('is_active',)
    list_select_related = ('item',)


admin.site.register(Item, ItemAdmin)
admin.site.register(Transaction, TransactionAdmin)
