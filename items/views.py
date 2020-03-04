from rest_framework import viewsets

from items.models import Item
from items.serializers import ItemSerializer


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint allowing Item operations"""
    queryset = Item.objects.all().order_by('-create_date')
    serializer_class = ItemSerializer
