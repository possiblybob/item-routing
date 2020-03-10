import uuid

from django.db import models


class InvalidStateTransitionError(Exception):
    """exception thrown when invalid transition is triggered"""


class InvalidStateError(Exception):
    """exception thrown when given status/location would create a Transaction in an invalid state"""


class Choices(object):
    """base set of choices for Transactions and Items"""

    @classmethod
    def choices(cls):
        """defines available choices built using per-type values"""


class TransactionLocation(Choices):
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


class TransactionStatus(Choices):
    """a given status for funds in a Transaction"""
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    ERROR = 'error'
    REFUNDING = 'refunding'
    REFUNDED = 'refunded'
    FIXING = 'fixing'

    @classmethod
    def choices(cls):
        """selectable choices for Statuses"""
        return (
            (TransactionStatus.PROCESSING, 'Processing'),
            (TransactionStatus.COMPLETED, 'Completed'),
            (TransactionStatus.ERROR, 'Error'),
            (TransactionStatus.REFUNDING, 'Refunding'),
            (TransactionStatus.REFUNDED, 'Refunded'),
            (TransactionStatus.FIXING, 'Fixing'),
        )


class ItemState(Choices):
    """defines states for an Item relative to its associated Transaction"""
    PROCESSING = 'processing'
    CORRECTING = 'correcting'
    ERROR = 'error'
    RESOLVED = 'resolved'

    @classmethod
    def choices(cls):
        """selectable choices for States"""
        return (
            (ItemState.PROCESSING, 'First Time Processing'),
            (ItemState.CORRECTING, 'Any Unfinished Correction'),
            (ItemState.ERROR, 'Error'),
            (ItemState.RESOLVED, 'Positive Finish State'),
        )


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
    state = models.CharField(max_length=20, choices=ItemState.choices(), default=ItemState.PROCESSING)
    has_errored = models.BooleanField(
        default=False, help_text='Whether or not processing of this Item has ever errored'
    )

    def __str__(self):
        return "Item<{}>".format(str(self.id))

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

    def create_transaction(self, initial_status=TransactionStatus.PROCESSING, initial_location=TransactionLocation.ORIGINATOR_BANK):
        """creates a new Transaction, marking any previous transaction as inactive"""
        if not (initial_status and initial_location):
            raise InvalidStateError('Status and Location are required to create a valid Transaction state')

        # validate initial status/location
        if not Transaction.is_valid_start_state(initial_status, initial_location):
            raise InvalidStateError('Invalid Status/Location provided to create a valid Transaction state')

        transaction = Transaction(
            item=self,
            status=initial_status,
            location=initial_location,
            is_active=True
        )
        transaction.save()
        # ENHANCEMENT: handle in DB transaction
        # ensure other Transactions for this item are inactive
        for existing_transaction in Transaction.objects.filter(item=self, is_active=True).exclude(id=transaction.id):
            existing_transaction.mark_inactive()
        self.transaction = transaction
        self.save()
        return transaction

    def begin_refund(self):
        """creates new Transaction to begin refunding amount to originator"""
        if not self.transaction:
            # no refundable transaction associated with item
            raise InvalidStateTransitionError('{} does not have a Transaction that can be refunded'.format(self))
        elif self.transaction.status != TransactionStatus.ERROR:
            # transaction not in fixable status
            raise InvalidStateTransitionError('Transaction {} is not in a state that can be refunded'.format(self.transaction))

        # create a new Transaction that can be refunded
        return self.create_transaction(
            initial_status=TransactionStatus.REFUNDING, initial_location=TransactionLocation.ROUTABLE
        )

    def fix(self):
        """creates new Transaction to begin fixing an errored Transaction"""
        if not self.transaction:
            # no refundable transaction associated with item
            raise InvalidStateTransitionError('{} does not have a Transaction that can be fixed'.format(self))
        elif self.transaction.status != TransactionStatus.ERROR:
            # transaction not in fixable status
            raise InvalidStateTransitionError('Transaction {} is not in a state that can be fixed'.format(self.transaction))
        # create a new Transaction that can be fixed
        return self.create_transaction(
            initial_status=TransactionStatus.FIXING, initial_location=TransactionLocation.ROUTABLE
        )

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
        max_length=20, choices=TransactionLocation.choices(), default=TransactionLocation.ORIGINATOR_BANK,
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether or not this Transaction is currently the active Transaction for its Item'
    )

    def __str__(self):
        return "Transaction<{}>".format(str(self.id))

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        result = super(Transaction, self).save(*args, **kwargs)
        if is_new and self.item:
            self.update_item_status(new_transaction=True)

        return result

    def mark_inactive(self):
        """changes current active status for Transaction to inactive"""
        self.is_active = False
        self.save()
        self.update_item_status()

    def move(self):
        """moves Transaction from current state to next"""
        # ensure Transaction is not already completed
        if self.status in (TransactionStatus.COMPLETED, TransactionStatus.ERROR, TransactionStatus.REFUNDED):
            raise InvalidStateTransitionError('Transaction is not in a state that can be moved.')

        if self.location == TransactionLocation.ORIGINATOR_BANK:
            # move to internal processing state
            self.location = TransactionLocation.ROUTABLE
        elif self.location == TransactionLocation.ROUTABLE:
            if self.status == TransactionStatus.PROCESSING:
                # move to completed bank state
                self.location = TransactionLocation.DESTINATION_BANK
                self.status = TransactionStatus.COMPLETED
            elif self.status == TransactionStatus.FIXING:
                # move back into processing flow after error
                self.status = TransactionStatus.PROCESSING
            elif self.status == TransactionStatus.REFUNDING:
                # move refund back to originating bank
                self.status = TransactionStatus.REFUNDED
                self.location = TransactionLocation.ORIGINATOR_BANK

        self.save()
        self.update_item_status()

    def error(self):
        """moves Transaction from current state to error state"""
        if not (self.status == TransactionStatus.PROCESSING and self.location == TransactionLocation.ROUTABLE):
            raise InvalidStateTransitionError('Transaction is not in a state that can be marked as errored.')
        self.location = TransactionLocation.ROUTABLE
        self.status = TransactionStatus.ERROR
        self.save()
        self.update_item_status()

    def update_item_status(self, new_transaction=False):
        """updates item status based on current status"""
        if not self.is_active:
            # not currently the active Transaction for an Item so state change does not affect it
            return

        update = False
        new_state = None

        if new_transaction:
            # newly-created Transaction resets Item status new processing/correcting
            if self.item.has_errored:
                # Transaction has been attempted before but errored
                new_state = ItemState.CORRECTING
            else:
                # first Transaction just created
                new_state = ItemState.PROCESSING
        elif self.status == TransactionStatus.ERROR:
            # errored Transaction resets Item status to error
            new_state = ItemState.ERROR
            if not self.item.has_errored:
                # set flag for having errored during processing
                self.item.has_errored = True
                update = True
        elif self.status in (TransactionStatus.COMPLETED, TransactionStatus.REFUNDED):
            # reaching positive finish state resets Item status to resolved
            new_state = ItemState.RESOLVED

        if update or new_state and new_state != self.item.state:
            self.item.state = new_state
            self.item.save()

    @classmethod
    def is_valid_state(cls, status, location):
        """determines if the given status and location constitute a valid Transaction state"""
        if not (status and location):
            # both values required to determine state
            return False
        valid_states = (
            (TransactionStatus.PROCESSING, TransactionLocation.ORIGINATOR_BANK),  # State A
            (TransactionStatus.PROCESSING, TransactionLocation.ROUTABLE),  # State B
            (TransactionStatus.COMPLETED, TransactionLocation.DESTINATION_BANK),  # State C
            (TransactionStatus.ERROR, TransactionLocation.ROUTABLE),  # State D
            (TransactionStatus.REFUNDING, TransactionLocation.ROUTABLE),  # State E
            (TransactionStatus.REFUNDED, TransactionLocation.ORIGINATOR_BANK),  # State F
            (TransactionStatus.FIXING, TransactionLocation.ROUTABLE),  # State G
        )
        return (status, location) in valid_states

    @classmethod
    def is_valid_start_state(cls, status, location):
        """determines if the given status and location constitute a valid starting Transaction state"""
        if not cls.is_valid_state(status, location):
            return False
        valid_start_states = (
            (TransactionStatus.PROCESSING, TransactionLocation.ORIGINATOR_BANK),  # State A
            (TransactionStatus.REFUNDING, TransactionLocation.ROUTABLE),  # State E
            (TransactionStatus.FIXING, TransactionLocation.ROUTABLE),  # State G
        )
        return (status, location) in valid_start_states
