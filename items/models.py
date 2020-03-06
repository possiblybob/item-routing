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

    @property
    def status(self):
        """current status of Transaction associated with Item, if any"""
        if not self.transaction:
            return None
        return self.transaction.status

    @property
    def location(self):
        """current location of Transaction associated with Item, if any"""
        if not self.transaction:
            return None
        return self.transaction.location

    def create_transaction(self):
        """creates a new Transaction, marking any previous transaction as inactive"""
        transaction = Transaction.objects.create(item=self)
        # TODO: handle in DB transaction
        # ensure other Transactions for this item are inactive
        for existing_transaction in Transaction.objects.filter(item=self, is_active=True).exclude(id=transaction.id):
            existing_transaction.mark_inactive()
        self.transaction = transaction
        self.save()
        return transaction

    def move(self):
        """moves associated Transaction from current state to next"""
        if not self.transaction:
            raise InvalidStateTransitionError('{} does not have a Transaction that can be moved'.format(self))
        self.transaction.move()
        return self

    def error(self):
        """moves associated Transaction from current state to error state"""
        if not self.transaction:
            raise InvalidStateTransitionError('{} does not have a Transaction that can be errored'.format(self))
        self.transaction.error()
        return self


class TransactionChoices(object):
    """base set of choices for Transactions"""

    @classmethod
    def choices(cls):
        """defines available choices built using per-type values"""


class TransactionLocation(object):
    """a given location for funds in a Transaction"""
    ORIGINATOR_BANK = 'originator_bank'
    ROUTABLE = 'routable'
    DESTINATION_BANK = 'destination_bank'

    @classmethod
    def choices(cls):
        """selectable choices for Locations"""
        return (
            (TransactionLocation.ORIGINATOR_BANK, 'Originator Bank'),
            (TransactionLocation.ROUTABLE, 'Routable'),
            (TransactionLocation.DESTINATION_BANK, 'Destination Bank'),
        )


class TransactionStatus(object):
    """a given status for funds in a Transaction"""
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    ERROR = 'error'

    @classmethod
    def choices(cls):
        """selectable choices for Locations"""
        return (
            (TransactionStatus.PROCESSING, 'Processing'),
            (TransactionStatus.COMPLETED, 'Completed'),
            (TransactionStatus.ERROR, 'Error'),
        )


class Transaction(models.Model):
    """an action applied to an Item"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    item = models.ForeignKey(Item, related_name='transactions', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.PROCESSING
    )
    location = models.CharField(
        max_length=20, choices=TransactionLocation.choices(), default=TransactionLocation.ORIGINATOR_BANK
    )
    is_active = models.BooleanField(default=True)

    def get_location(self):
        """converts stored location to enumerated type"""
        if not self.location:
            return None
        return TransactionLocation.from_name(self.location)

    def get_status(self):
        """converts stored status to enumerated type"""
        if not self.status:
            return None
        return TransactionStatus.from_name(self.status)

    def mark_inactive(self):
        """changes current active status for Transaction to inactive"""
        self.is_active = False
        self.save()

    def move(self):
        """moves Transaction from current state to next"""
        # ensure Transaction is not already completed
        if self.status in (TransactionStatus.COMPLETED, TransactionStatus.ERROR):
            raise InvalidStateTransitionError('Transaction is not in a state that can be moved.')

        if self.location == TransactionLocation.ORIGINATOR_BANK:
            # move to internal processing state
            self.location = TransactionLocation.ROUTABLE
        elif self.location == TransactionLocation.ROUTABLE:
            # move to completed bank state
            self.location = TransactionLocation.DESTINATION_BANK
            self.status = TransactionStatus.COMPLETED
        self.save()

    def error(self):
        """moves Transaction from current state to error state"""
        if not (self.status == TransactionStatus.PROCESSING and self.location == TransactionLocation.ROUTABLE):
            raise InvalidStateTransitionError('Transaction is not in a state that can be marked as errored.')
        self.location = TransactionLocation.ROUTABLE
        self.status = TransactionStatus.ERROR
        self.save()
