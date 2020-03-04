import uuid

from enum import Enum
from django.db import models


class Item(models.Model):
    """a payment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    amount = models.BigIntegerField()


class TransactionEnum(Enum):
    """common enumeration for Transaction values"""

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)


class TransactionLocation(TransactionEnum):
    """a given location for funds in a Transaction"""
    originator_bank = 'Origination Bank'
    routable = 'Routable'
    destination_bank = 'Destination Bank'


class TransactionStatus(TransactionEnum):
    """a given status for funds in a Transaction"""
    processing = 'Processing'
    completed = 'Completed'
    error = 'Error'


class Transaction(models.Model):
    """an action applied to an Item"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    item = models.ForeignKey(Item, related_name='transactions', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.processing
    )
    location = models.CharField(
        max_length=20, choices=TransactionLocation.choices(), default=TransactionLocation.originator_bank
    )
