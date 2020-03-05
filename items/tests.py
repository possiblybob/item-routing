from django.test import TestCase
from decimal import Decimal
from items.models import Item, Transaction, TransactionLocation, TransactionStatus, \
    InvalidStateTransitionError
from uuid import UUID


class UUIDTestCase(TestCase):
    """tests UUID models"""

    @staticmethod
    def is_uuid(value, version=4):
        """tests if value is a valid UUID4"""
        if isinstance(value, UUID):
            return True

        try:
            uuid_val = UUID(value, version=version)
        except ValueError:
            # unable to parse as a UUID
            return False

        return str(uuid_val) == value


class ItemTestCase(UUIDTestCase):
    """tests features related to Items"""

    def setUp(self):
        self.default_amount = Decimal('42')

    def _create_item(self, amount=None):
        if amount is None:
            amount = self.default_amount
        return Item.objects.create(amount=amount)

    def test_id_is_uuid(self):
        """tests that Item identifier is a UUID"""
        item = self._create_item()
        self.assertTrue(self.is_uuid(item.id))

    def test_move(self):
        """tests moving a Item progresses its current Transaction to the correct state"""
        item = self._create_item()

        # verify moving without a Transaction causes an error
        with self.assertRaises(InvalidStateTransitionError):
            item.move()

        # create Transaction for item
        item.create_transaction()

        # verify initial state
        self.assertEqual(item.transaction.status, TransactionStatus.processing)
        self.assertEqual(item.transaction.location, TransactionLocation.originator_bank)

        # verify progressed to next state
        item.move()
        self.assertEqual(item.transaction.status, TransactionStatus.processing)
        self.assertEqual(item.transaction.location, TransactionLocation.routable)

        # verify progressed to final success state
        item.move()
        self.assertEqual(item.transaction.status, TransactionStatus.completed)
        self.assertEqual(item.transaction.location, TransactionLocation.destination_bank)

        # verify move from completed state is invalid
        with self.assertRaises(InvalidStateTransitionError):
            item.move()

        # verify move from errored state is invalid
        item = self._create_item()
        item.create_transaction()  # processing/originator
        item.move()  # processing/routable
        item.error()  # error/routable
        self.assertEqual(item.transaction.status, TransactionStatus.error)
        self.assertEqual(item.transaction.location, TransactionLocation.routable)
        with self.assertRaises(InvalidStateTransitionError):
            item.move()

    def test_error(self):
        """tests error a Item progresses its current Transaction to the correct state"""
        item = self._create_item()

        # verify moving without a Transaction causes an error
        with self.assertRaises(InvalidStateTransitionError):
            item.error()

        # create Transaction for item
        item.create_transaction()

        # verify erroring in initial state is invalid
        with self.assertRaises(InvalidStateTransitionError):
            item.error()

        item.move()
        self.assertEqual(item.transaction.status, TransactionStatus.processing)
        self.assertEqual(item.transaction.location, TransactionLocation.routable)

        # verify erroring in processing state moves to correct state
        item.error()
        self.assertEqual(item.transaction.status, TransactionStatus.error)
        self.assertEqual(item.transaction.location, TransactionLocation.routable)

        # verify erroring in errored state is invalid
        with self.assertRaises(InvalidStateTransitionError):
            item.error()

        # verify erroring from completed state is invalid
        item = self._create_item()
        item.create_transaction()  # processing/originator
        item.move()  # processing/routable
        item.move()  # completed/destination

        with self.assertRaises(InvalidStateTransitionError):
            item.error()

    def test_create_transaction(self):
        """creates a new Transaction, marking any previous transaction as inactive"""
        item = self._create_item()
        # verify initial state has no Transaction
        self.assertIsNone(item.transaction)

        # verify creating new Transaction associates with Item
        item.create_transaction()
        transaction = item.transaction
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.item, item)
        self.assertTrue(transaction.is_active)

        # verify creating new Transaction creates a second transaction, still associated with item
        item.create_transaction()
        second_transaction = item.transaction
        self.assertIsNotNone(second_transaction)
        self.assertEqual(second_transaction.item, item)
        self.assertNotEqual(transaction, second_transaction)
        self.assertTrue(second_transaction.is_active)

        # refresh Transaction to get current state
        transaction = Transaction.objects.get(id=transaction.pk)
        self.assertFalse(transaction.is_active)

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


class TransactionTestCase(UUIDTestCase):
    """tests features related to Transactions"""

    def setUp(self):
        """sets up initial state for each test"""
        amount = Decimal('42')
        self.test_item = Item.objects.create(amount=amount)

    def _create_transaction(self, initial_status=None, initial_location=None):
        create_kwargs = {
            'item': self.test_item
        }
        if initial_status is not None:
            create_kwargs['status'] = initial_status
        if initial_location is not None:
            create_kwargs['location'] = initial_location
        return Transaction.objects.create(**create_kwargs)

    def test_id_is_uuid(self):
        """tests that Transaction identifier is a UUID"""
        transaction = self._create_transaction()
        self.assertIsNotNone(transaction)
        self.assertTrue(self.is_uuid(transaction.id))

    def test_mark_inactive(self):
        """tests marking Tranaction as inactive updates status"""
        transaction = self._create_transaction()
        self.assertTrue(transaction.is_active)
        transaction.mark_inactive()
        self.assertFalse(transaction.is_active)

    def test_move(self):
        """tests moving a Transaction progresses to the correct states"""
        transaction = self._create_transaction()

        # verify initial state
        self.assertEqual(transaction.status, TransactionStatus.processing)
        self.assertEqual(transaction.location, TransactionLocation.originator_bank)

        # verify progressed to next state
        transaction.move()
        self.assertEqual(transaction.status, TransactionStatus.processing)
        self.assertEqual(transaction.location, TransactionLocation.routable)

        # verify progressed to final success state
        transaction.move()
        self.assertEqual(transaction.status, TransactionStatus.completed)
        self.assertEqual(transaction.location, TransactionLocation.destination_bank)

        # verify move from final status is invalid
        with self.assertRaises(InvalidStateTransitionError):
            transaction.move()

    def test_error(self):
        """tests erroring a Transaction progresses to the correct state"""

        # verify erroring at initial state leads is invalid
        processing_originator = self._create_transaction()
        with self.assertRaises(InvalidStateTransitionError):
            processing_originator.error()

        # verify erroring at Routable/processing state leads to error state
        processing_routable = self._create_transaction(
            initial_location=TransactionLocation.routable, initial_status=TransactionStatus.processing
        )
        processing_routable.error()
        self.assertEqual(processing_routable.status, TransactionStatus.error)
        self.assertEqual(processing_routable.location, TransactionLocation.routable)

        # verify erroring at Destination/completed is invalid
        destination_completed = self._create_transaction(
            initial_location=TransactionLocation.destination_bank, initial_status=TransactionStatus.completed
        )
        with self.assertRaises(InvalidStateTransitionError):
            destination_completed.error()
