# item-routing

This project creates a series of transaction flows for items. It uses the [Django REST Framework](https://www.django-rest-framework.org/)
and [Django Object Actions](https://pypi.org/project/django-object-actions/) packages to allow the movements of a payment item between various states.

## Workflows

Creating and moving items through the preset steps requires the following API method
calls and admin site interactions. For all examples, the `[ITEM_ID]` value is a valid
UUID, the `[HOST]` value is website root, and `[AMOUNT]` is some decimal dollar amount.

### Successful Flow

```
POST [HOST]/api/v1/items/ {"amount": [AMOUNT]}
POST [HOST]/api/v1/items/[ITEM_ID]/create_transaction/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
```

### Error/Fix Flow

```
POST [HOST]/api/v1/items/ {"amount": [AMOUNT]}
POST [HOST]/api/v1/items/[ITEM_ID]/create_transaction/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
PUT  [HOST]/api/v1/items/[ITEM_ID]/error/
PUT  [HOST]/api/v1/items/[ITEM_ID]/fix/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
```

### Error/Refund Flow

```
POST [HOST]/api/v1/items/ {"amount": [AMOUNT]}
POST [HOST]/api/v1/items/[ITEM_ID]/create_transaction/
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
PUT  [HOST]/api/v1/items/[ITEM_ID]/error/
Click "Refund" button through the website admin page for [ITEM_ID]
PUT  [HOST]/api/v1/items/[ITEM_ID]/move/
```
