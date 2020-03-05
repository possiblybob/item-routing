import uuid

from enum import Enum
from django.db import models


class InvalidStateTransitionError(Exception):
    """exception thrown when invalid transition is triggered"""


class Item(models.Model):
    """a payment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # active transaction
    transaction = models.ForeignKey(
        'Transaction', null=True, blank=True, related_name='current_transaction', on_delete=models.SET_NULL
    )

    def create_transaction(self):
        """creates a new Transaction, marking any previous transaction as inactive"""
        transaction = Transaction.objects.create(item=self)
        # TODO: handle in DB transaction
        if self.transaction:
            self.transaction.mark_inactive()
        self.transaction = transaction
        self.save()

    def move(self):
        """moves associated Transaction from current state to next"""
        if not self.transaction:
            raise InvalidStateTransitionError('{} does not have a Transaction that can be moved'.format(self))
        self.transaction.move()

    def error(self):
        """moves associated Transaction from current state to error state"""
        if not self.transaction:
            raise InvalidStateTransitionError('{} does not have a Transaction that can be errored'.format(self))
        self.transaction.error()


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
    is_active = models.BooleanField(default=True)

    def mark_inactive(self):
        """changes current active status for Transaction to inactive"""
        self.is_active = False
        self.save()

    def move(self):
        """moves Transaction from current state to next"""
        # ensure Transaction is not already completed
        if self.status in (TransactionStatus.completed, TransactionStatus.error):
            raise InvalidStateTransitionError('Transaction is not in a state that can be moved.')

        if self.location == TransactionLocation.originator_bank:
            # move to internal processing state
            self.location = TransactionLocation.routable
        elif self.location == TransactionLocation.routable:
            # move to completed bank state
            self.location = TransactionLocation.destination_bank
            self.status = TransactionStatus.completed

        self.save()

    def error(self):
        """moves Transaction from current state to error state"""
        if not (self.status == TransactionStatus.processing and self.location == TransactionLocation.routable):
            raise InvalidStateTransitionError('Transaction is not in a state that can be marked as errored.')
        self.location = TransactionLocation.routable
        self.status = TransactionStatus.error
        self.save()
