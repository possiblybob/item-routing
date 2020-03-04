import uuid

from enum import Enum
from django.db import models


class Item(models.Model):
    """a payment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4(), editable=False)
    amount = models.BigIntegerField()


class TransactionLocation(Enum):
    """a given location for funds in a Transaction"""
    ORIGINATION_BANK = 'Origination Bank'
    ROUTABLE = 'Routable'
    DESTINATION_BANK = 'Destination Bank'


class TransactionStatus(Enum):
    """a given status for funds in a Transaction"""
    PROCESSING = 'Processing'
    COMPLETED = 'Completed'
    ERROR = 'Error'


class Transaction(models.Model):
    """an action applied to an Item"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4(), editable=False)
    item = models.ForeignKey(Item, related_name='transactions', on_delete=models.CASCADE)
    status = models.CharField(
        blank=True, null=True, max_length=20,
        choices=[(tag, tag.value) for tag in TransactionStatus]
    )
    location = models.CharField(
        blank=True, null=True, max_length=20,
        choices=[(tag, tag.value) for tag in TransactionLocation]
    )
    create_date = models.DateTimeField(auto_now_add=True)
