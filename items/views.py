from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from items.models import Item, Transaction, InvalidStateTransitionError
from items.serializers import ItemSerializer, TransactionSerializer


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint allowing Item operations"""
    queryset = Item.objects.all().order_by('-create_date')
    serializer_class = ItemSerializer

    @action(detail=True, methods=['post'])
    def create_transaction(self, request, pk=None):
        """creates a Transaction for the given Item"""
        item = self.get_object()
        transaction = item.create_transaction()

        # response should have current Item values and success message
        serializer = ItemSerializer(
            item,
            context={
                'request': request
            }
        )
        response_data = serializer.data
        response_data['status'] = 'Transaction {} created'.format(transaction.id)
        return Response(response_data)

    @action(detail=True, methods=['put'])
    def move(self, request, pk=None):
        """moves Item from the current state to the next"""
        item = self.get_object()

        try:
            item.move()
        except InvalidStateTransitionError as ex:
            return Response(
                data={
                    'error': str(ex)
                },
                status=status.HTTP_400_BAD_REQUEST,
                exception=True
            )
        else:
            # response should have current Item values and success message
            serializer = ItemSerializer(
                item,
                context={
                    'request': request
                }
            )
            response_data = serializer.data
            response_data['status'] = 'Item moved to {}/{}'.format(item.status, item.location)
            return Response(response_data)

    @action(detail=True, methods=['put'])
    def error(self, request, pk=None):
        """moves Item into the error state"""
        item = self.get_object()

        try:
            item.error()
        except InvalidStateTransitionError as ex:
            return Response(
                data={
                    'error': str(ex)
                },
                status=status.HTTP_400_BAD_REQUEST,
                exception=True
            )
        else:
            # response should have current Item values and success message
            serializer = ItemSerializer(
                item,
                context={
                    'request': request
                }
            )
            response_data = serializer.data
            response_data['status'] = 'Item errored'
            return Response(response_data)

    @action(detail=True, methods=['put'])
    def fix(self, request, pk=None):
        """moves Item from the current state to the next"""
        item = self.get_object()

        try:
            item.fix()
        except InvalidStateTransitionError as ex:
            return Response(
                data={
                    'error': str(ex)
                },
                status=status.HTTP_400_BAD_REQUEST,
                exception=True
            )
        else:
            # response should have current Item values and success message
            serializer = ItemSerializer(
                item,
                context={
                    'request': request
                }
            )
            response_data = serializer.data
            response_data['status'] = 'Item fixed'
            return Response(response_data)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint viewing of Transactions"""
    queryset = Transaction.objects.all().order_by('-create_date')
    serializer_class = TransactionSerializer
