---
title: Payment Intents
url: https://stripe.com/docs/api/payment_intents
hostname: stripe.com
sitename: stripe.com
date: 2025-12-19
---
A PaymentIntent guides you through the process of collecting a payment from your customer. We recommend that you create exactly one PaymentIntent for each order or customer session in your system. You can reference the PaymentIntent later to see the history of payment attempts for a particular session.

A PaymentIntent transitions through [multiple statuses](https://stripe.com/payments/paymentintents/lifecycle) throughout its lifetime as it interfaces with Stripe.js to perform authentication flows and ultimately creates at most one successful charge.

Related guide: [Payment Intents API](https://stripe.com/payments/payment-intents)

[POST/](https://stripe.com/api/payment_intents/create) v1/ payment_intents

[POST/](https://stripe.com/api/payment_intents/update) v1/ payment_intents/ :id

[GET/](https://stripe.com/api/payment_intents/retrieve) v1/ payment_intents/ :id

[GET/](https://stripe.com/api/payment_intents/amount_details_line_items) v1/ payment_intents/ :id/ amount_details_line_items

[GET/](https://stripe.com/api/payment_intents/list) v1/ payment_intents

[POST/](https://stripe.com/api/payment_intents/cancel) v1/ payment_intents/ :id/ cancel

[POST/](https://stripe.com/api/payment_intents/capture) v1/ payment_intents/ :id/ capture

[POST/](https://stripe.com/api/payment_intents/confirm) v1/ payment_intents/ :id/ confirm

[POST/](https://stripe.com/api/payment_intents/increment_authorization) v1/ payment_intents/ :id/ increment_authorization

[POST/](https://stripe.com/api/payment_intents/apply_customer_balance) v1/ payment_intents/ :id/ apply_customer_balance

[GET/](https://stripe.com/api/payment_intents/search) v1/ payment_intents/ search

[POST/](https://stripe.com/api/payment_intents/verify_microdeposits) v1/ payment_intents/ :id/ verify_microdeposits

### Attributes

- idstringretrievable with publishable key
Unique identifier for the object.

- amountintegerretrievable with publishable key
Amount intended to be collected by this PaymentIntent. A positive integer representing how much to charge in the

[smallest currency unit](https://stripe.com/currencies#zero-decimal)(e.g., 100 cents to charge $1.00 or 100 to charge ¥100, a zero-decimal currency). The minimum amount is $0.50 US or[equivalent in charge currency](https://stripe.com/currencies#minimum-and-maximum-charge-amounts). The amount value supports up to eight digits (e.g., a value of 99999999 for a USD charge of $999,999.99). - automatic_
payment_ methodsnullable objectretrievable with publishable key Settings to configure compatible payment methods from the

[Stripe Dashboard](https://dashboard.stripe.com/settings/payment_methods) - client_
secretnullable stringretrievable with publishable key The client secret of this PaymentIntent. Used for client-side retrieval using a publishable key.

The client secret can be used to complete a payment from your frontend. It should not be stored, logged, or exposed to anyone other than the customer. Make sure that you have TLS enabled on any page that includes the client secret.

Refer to our docs to

[accept a payment](https://stripe.com/payments/accept-a-payment?ui=elements)and learn about how`client_`

should be handled.secret - currencyenumretrievable with publishable key
Three-letter

[ISO currency code](https://www.iso.org/iso-4217-currency-codes.html), in lowercase. Must be a[supported currency](https://stripe.com/docs/currencies). - customernullable stringExpandable
ID of the Customer this PaymentIntent belongs to, if one exists.

Payment methods attached to other Customers cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Customer after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Customer instead. - customer_
accountnullable string ID of the Account representing the customer that this PaymentIntent belongs to, if one exists.

Payment methods attached to other Accounts cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Account after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Account instead. - descriptionnullable stringretrievable with publishable key
An arbitrary string attached to the object. Often useful for displaying to users.

- last_
payment_ errornullable objectretrievable with publishable key The payment error encountered in the previous PaymentIntent confirmation. It will be cleared if the PaymentIntent is later updated for any reason.

- latest_
chargenullable stringExpandable ID of the latest

[Charge object](https://stripe.com/api/charges)created by this PaymentIntent. This property is`null`

until PaymentIntent confirmation is attempted. - metadataobject
Set of

[key-value pairs](https://stripe.com/api/metadata)that you can attach to an object. This can be useful for storing additional information about the object in a structured format. Learn more about[storing information in metadata](https://stripe.com/payments/payment-intents/creating-payment-intents#storing-information-in-metadata). - next_
actionnullable objectretrievable with publishable key If present, this property tells you what actions you need to take in order for your customer to fulfill a payment using the provided source.

- payment_
methodnullable stringExpandableretrievable with publishable key ID of the payment method used in this PaymentIntent.

- receipt_
emailnullable stringretrievable with publishable key Email address that the receipt for the resulting payment will be sent to. If

`receipt_`

is specified for a payment in live mode, a receipt will be sent regardless of youremail [email settings](https://dashboard.stripe.com/account/emails). - setup_
future_ usagenullable enumretrievable with publishable key Indicates that you intend to make future payments with this PaymentIntent’s payment method.

If you provide a Customer with the PaymentIntent, you can use this parameter to

[attach the payment method](https://stripe.com/payments/save-during-payment)to the Customer after the PaymentIntent is confirmed and the customer completes any required actions. If you don’t provide a Customer, you can still[attach](https://stripe.com/api/payment_methods/attach)the payment method to a Customer after the transaction completes.If the payment method is

`card_`

and isn’t a digital wallet, Stripe creates and attaches apresent [generated_card](https://stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card to the Customer instead.When processing card payments, Stripe uses

`setup_`

to help you comply with regional legislation and network rules, such asfuture_ usage [SCA](https://stripe.com/strong-customer-authentication).Possible enum values`off_`

session Use

`off_`

if your customer may or may not be present in your checkout flow.session `on_`

session Use

`on_`

if you intend to only reuse the payment method when your customer is present in your checkout flow.session - shippingnullable objectretrievable with publishable key
Shipping information for this PaymentIntent.

- statement_
descriptornullable string Text that appears on the customer’s statement as the statement descriptor for a non-card charge. This value overrides the account’s default statement descriptor. For information about requirements, including the 22-character limit, see

[the Statement Descriptor docs](https://docs.stripe.com/get-started/account/statement-descriptors).Setting this value for a card charge returns an error. For card charges, set the

[statement_descriptor_suffix](https://docs.stripe.com/get-started/account/statement-descriptors#dynamic)instead. - statement_
descriptor_ suffixnullable string Provides information about a card charge. Concatenated to the account’s

[statement descriptor prefix](https://docs.stripe.com/get-started/account/statement-descriptors#static)to form the complete statement descriptor that appears on the customer’s statement. - statusenumretrievable with publishable key
Status of this PaymentIntent, one of

`requires_`

,payment_ method `requires_`

,confirmation `requires_`

,action `processing`

,`requires_`

,capture `canceled`

, or`succeeded`

. Read more about each PaymentIntent[status](https://stripe.com/payments/intents#intent-statuses).Possible enum values`canceled`

The PaymentIntent has been canceled.

`processing`

The PaymentIntent is currently being processed.

`requires_`

action The PaymentIntent requires additional action from the customer.

`requires_`

capture The PaymentIntent has been confirmed and requires capture.

`requires_`

confirmation The PaymentIntent requires confirmation.

`requires_`

payment_ method The PaymentIntent requires a payment method to be attached.

`succeeded`

The PaymentIntent has succeeded.


### More attributes

- objectstringretrievable with publishable key
- amount_
capturableinteger - amount_
detailsnullable object - amount_
receivedinteger - applicationnullable stringExpandableConnect only
- application_
fee_ amountnullable integerConnect only - canceled_
atnullable timestampretrievable with publishable key - cancellation_
reasonnullable enumretrievable with publishable key - capture_
methodenumretrievable with publishable key - confirmation_
methodenumretrievable with publishable key - createdtimestampretrievable with publishable key
- excluded_
payment_ method_ typesnullable array of enums - hooksnullable object
- livemodebooleanretrievable with publishable key
- on_
behalf_ ofnullable stringExpandableConnect only - payment_
detailsnullable object - payment_
method_ configuration_ detailsnullable object - payment_
method_ optionsnullable object - payment_
method_ typesarray of stringsretrievable with publishable key - presentment_
detailsnullable object - processingnullable objectretrievable with publishable key
- reviewnullable stringExpandable
- transfer_
datanullable objectConnect only - transfer_
groupnullable stringConnect only

`{ "id": "pi_3MtwBwLkdIwHu7ix28a3tqPa", "object": "payment_intent", "amount": 2000, "amount_capturable": 0, "amount_details": { "tip": {} }, "amount_received": 0, "application": null, "application_fee_amount": null, "automatic_payment_methods": { "enabled": true }, "canceled_at": null, "cancellation_reason": null, "capture_method": "automatic", "client_secret": "pi_3MtwBwLkdIwHu7ix28a3tqPa_secret_YrKJUKribcBjcG8HVhfZluoGH", "confirmation_method": "automatic", "created": 1680800504, "currency": "usd", "customer": null, "description": null, "last_payment_error": null, "latest_charge": null, "livemode": false, "metadata": {}, "next_action": null, "on_behalf_of": null, "payment_method": null, "payment_method_options": { "card": { "installments": null, "mandate_options": null, "network": null, "request_three_d_secure": "automatic" }, "link": { "persistent_token": null } }, "payment_method_types": [ "card", "link" ], "processing": null, "receipt_email": null, "review": null, "setup_future_usage": null, "shipping": null, "source": null, "statement_descriptor": null, "statement_descriptor_suffix": null, "status": "requires_payment_method", "transfer_data": null, "transfer_group": null}`


Creates a PaymentIntent object.

After the PaymentIntent is created, attach a payment method and [confirm](https://stripe.com/api/payment_intents/confirm) to continue the payment. Learn more about [the available payment flows with the Payment Intents API](https://stripe.com/payments/payment-intents).

When you use `confirm=true`

during creation, it’s equivalent to creating and confirming the PaymentIntent in the same call. You can use any parameters available in the [confirm API](https://stripe.com/api/payment_intents/confirm) when you supply `confirm=true`

.

### Parameters

- amountintegerRequired
Amount intended to be collected by this PaymentIntent. A positive integer representing how much to charge in the

[smallest currency unit](https://stripe.com/currencies#zero-decimal)(e.g., 100 cents to charge $1.00 or 100 to charge ¥100, a zero-decimal currency). The minimum amount is $0.50 US or[equivalent in charge currency](https://stripe.com/currencies#minimum-and-maximum-charge-amounts). The amount value supports up to eight digits (e.g., a value of 99999999 for a USD charge of $999,999.99). - currencyenumRequired
Three-letter

[ISO currency code](https://www.iso.org/iso-4217-currency-codes.html), in lowercase. Must be a[supported currency](https://stripe.com/docs/currencies). - automatic_
payment_ methodsobject When you enable this parameter, this PaymentIntent accepts payment methods that you enable in the Dashboard and that are compatible with this PaymentIntent’s other parameters.

- confirmboolean
Set to

`true`

to attempt to[confirm this PaymentIntent](https://stripe.com/api/payment_intents/confirm)immediately. This parameter defaults to`false`

. When creating and confirming a PaymentIntent at the same time, you can also provide the parameters available in the[Confirm API](https://stripe.com/api/payment_intents/confirm). - customerstring
ID of the Customer this PaymentIntent belongs to, if one exists.

Payment methods attached to other Customers cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Customer after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Customer instead. - customer_
accountstring ID of the Account representing the customer that this PaymentIntent belongs to, if one exists.

Payment methods attached to other Accounts cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Account after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Account instead. - descriptionstring
An arbitrary string attached to the object. Often useful for displaying to users.

- metadataobject
Set of

[key-value pairs](https://stripe.com/api/metadata)that you can attach to an object. This can be useful for storing additional information about the object in a structured format. Individual keys can be unset by posting an empty value to them. All keys can be unset by posting an empty value to`metadata`

. - off_
sessionboolean | stringonly when confirm=true Set to

`true`

to indicate that the customer isn’t in your checkout flow during this payment attempt and can’t authenticate. Use this parameter in scenarios where you collect card details and[charge them later](https://stripe.com/payments/cards/charging-saved-cards). This parameter can only be used with.`confirm=true`

- payment_
methodstring ID of the payment method (a PaymentMethod, Card, or

[compatible Source](https://stripe.com/payments/payment-methods/transitioning#compatibility)object) to attach to this PaymentIntent.If you omit this parameter with

`confirm=true`

,`customer.`

attaches as this PaymentIntent’s payment instrument to improve migration for users of the Charges API. We recommend that you explicitly provide thedefault_ source `payment_`

moving forward. If the payment method is attached to a Customer, you must also provide the ID of that Customer as themethod [customer](https://stripe.com#create_payment_intent-customer)parameter of this PaymentIntent. - receipt_
emailstring Email address to send the receipt to. If you specify

`receipt_`

for a payment in live mode, you send a receipt regardless of youremail [email settings](https://dashboard.stripe.com/account/emails). - setup_
future_ usageenum Indicates that you intend to make future payments with this PaymentIntent’s payment method.

If you provide a Customer with the PaymentIntent, you can use this parameter to

[attach the payment method](https://stripe.com/payments/save-during-payment)to the Customer after the PaymentIntent is confirmed and the customer completes any required actions. If you don’t provide a Customer, you can still[attach](https://stripe.com/api/payment_methods/attach)the payment method to a Customer after the transaction completes.If the payment method is

`card_`

and isn’t a digital wallet, Stripe creates and attaches apresent [generated_card](https://stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card to the Customer instead.When processing card payments, Stripe uses

`setup_`

to help you comply with regional legislation and network rules, such asfuture_ usage [SCA](https://stripe.com/strong-customer-authentication).Possible enum values`off_`

session Use

`off_`

if your customer may or may not be present in your checkout flow.session `on_`

session Use

`on_`

if you intend to only reuse the payment method when your customer is present in your checkout flow.session - shippingobject
Shipping information for this PaymentIntent.

- statement_
descriptorstring Text that appears on the customer’s statement as the statement descriptor for a non-card charge. This value overrides the account’s default statement descriptor. For information about requirements, including the 22-character limit, see

[the Statement Descriptor docs](https://docs.stripe.com/get-started/account/statement-descriptors).Setting this value for a card charge returns an error. For card charges, set the

[statement_descriptor_suffix](https://docs.stripe.com/get-started/account/statement-descriptors#dynamic)instead. - statement_
descriptor_ suffixstring Provides information about a card charge. Concatenated to the account’s

[statement descriptor prefix](https://docs.stripe.com/get-started/account/statement-descriptors#static)to form the complete statement descriptor that appears on the customer’s statement.

### More parameters

- amount_
detailsobject - application_
fee_ amountintegerConnect only - capture_
methodenum - confirmation_
methodenum - confirmation_
tokenstringonly when confirm=true - error_
on_ requires_ actionbooleanonly when confirm=true - excluded_
payment_ method_ typesarray of enums - hooksobject
- mandatestringonly when confirm=true
- mandate_
dataobjectonly when confirm=true - on_
behalf_ ofstringConnect only - payment_
detailsobject - payment_
method_ configurationstring - payment_
method_ dataobject - payment_
method_ optionsobject - payment_
method_ typesarray of strings - radar_
optionsobject - return_
urlstringonly when confirm=true - transfer_
dataobjectConnect only - transfer_
groupstringConnect only - use_
stripe_ sdkboolean

### Returns

Returns a PaymentIntent object.

`{ "id": "pi_3MtwBwLkdIwHu7ix28a3tqPa", "object": "payment_intent", "amount": 2000, "amount_capturable": 0, "amount_details": { "tip": {} }, "amount_received": 0, "application": null, "application_fee_amount": null, "automatic_payment_methods": { "enabled": true }, "canceled_at": null, "cancellation_reason": null, "capture_method": "automatic", "client_secret": "pi_3MtwBwLkdIwHu7ix28a3tqPa_secret_YrKJUKribcBjcG8HVhfZluoGH", "confirmation_method": "automatic", "created": 1680800504, "currency": "usd", "customer": null, "description": null, "last_payment_error": null, "latest_charge": null, "livemode": false, "metadata": {}, "next_action": null, "on_behalf_of": null, "payment_method": null, "payment_method_options": { "card": { "installments": null, "mandate_options": null, "network": null, "request_three_d_secure": "automatic" }, "link": { "persistent_token": null } }, "payment_method_types": [ "card", "link" ], "processing": null, "receipt_email": null, "review": null, "setup_future_usage": null, "shipping": null, "source": null, "statement_descriptor": null, "statement_descriptor_suffix": null, "status": "requires_payment_method", "transfer_data": null, "transfer_group": null}`


Updates properties on a PaymentIntent object without confirming.

Depending on which properties you update, you might need to confirm the PaymentIntent again. For example, updating the `payment_`

always requires you to confirm the PaymentIntent again. If you prefer to update and confirm at the same time, we recommend updating properties through the [confirm API](https://stripe.com/api/payment_intents/confirm) instead.

### Parameters

- amountinteger
Amount intended to be collected by this PaymentIntent. A positive integer representing how much to charge in the

[smallest currency unit](https://stripe.com/currencies#zero-decimal)(e.g., 100 cents to charge $1.00 or 100 to charge ¥100, a zero-decimal currency). The minimum amount is $0.50 US or[equivalent in charge currency](https://stripe.com/currencies#minimum-and-maximum-charge-amounts). The amount value supports up to eight digits (e.g., a value of 99999999 for a USD charge of $999,999.99). - currencyenum
Three-letter

[ISO currency code](https://www.iso.org/iso-4217-currency-codes.html), in lowercase. Must be a[supported currency](https://stripe.com/docs/currencies). - customerstring
ID of the Customer this PaymentIntent belongs to, if one exists.

Payment methods attached to other Customers cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Customer after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Customer instead. - customer_
accountstring ID of the Account representing the customer that this PaymentIntent belongs to, if one exists.

Payment methods attached to other Accounts cannot be used with this PaymentIntent.

If

[setup_future_usage](https://stripe.com#payment_intent_object-setup_future_usage)is set and this PaymentIntent’s payment method is not`card_`

, then the payment method attaches to the Account after the PaymentIntent has been confirmed and any required actions from the user are complete. If the payment method ispresent `card_`

and isn’t a digital wallet, then apresent [generated_card](https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card is created and attached to the Account instead. - descriptionstring
An arbitrary string attached to the object. Often useful for displaying to users.

- metadataobject
Set of

[key-value pairs](https://stripe.com/api/metadata)that you can attach to an object. This can be useful for storing additional information about the object in a structured format. Individual keys can be unset by posting an empty value to them. All keys can be unset by posting an empty value to`metadata`

. - payment_
methodstring ID of the payment method (a PaymentMethod, Card, or

[compatible Source](https://stripe.com/payments/payment-methods/transitioning#compatibility)object) to attach to this PaymentIntent. To unset this field to null, pass in an empty string. - receipt_
emailstring Email address that the receipt for the resulting payment will be sent to. If

`receipt_`

is specified for a payment in live mode, a receipt will be sent regardless of youremail [email settings](https://dashboard.stripe.com/account/emails). - setup_
future_ usageenum Indicates that you intend to make future payments with this PaymentIntent’s payment method.

If you provide a Customer with the PaymentIntent, you can use this parameter to

[attach the payment method](https://stripe.com/payments/save-during-payment)to the Customer after the PaymentIntent is confirmed and the customer completes any required actions. If you don’t provide a Customer, you can still[attach](https://stripe.com/api/payment_methods/attach)the payment method to a Customer after the transaction completes.If the payment method is

`card_`

and isn’t a digital wallet, Stripe creates and attaches apresent [generated_card](https://stripe.com/api/charges/object#charge_object-payment_method_details-card_present-generated_card)payment method representing the card to the Customer instead.When processing card payments, Stripe uses

`setup_`

to help you comply with regional legislation and network rules, such asfuture_ usage [SCA](https://stripe.com/strong-customer-authentication).If you’ve already set

`setup_`

and you’re performing a request using a publishable key, you can only update the value fromfuture_ usage `on_`

tosession `off_`

.session Possible enum values`off_`

session Use

`off_`

if your customer may or may not be present in your checkout flow.session `on_`

session Use

`on_`

if you intend to only reuse the payment method when your customer is present in your checkout flow.session - shippingobject
Shipping information for this PaymentIntent.

- statement_
descriptorstring Text that appears on the customer’s statement as the statement descriptor for a non-card charge. This value overrides the account’s default statement descriptor. For information about requirements, including the 22-character limit, see

[the Statement Descriptor docs](https://docs.stripe.com/get-started/account/statement-descriptors).Setting this value for a card charge returns an error. For card charges, set the

[statement_descriptor_suffix](https://docs.stripe.com/get-started/account/statement-descriptors#dynamic)instead. - statement_
descriptor_ suffixstring Provides information about a card charge. Concatenated to the account’s

[statement descriptor prefix](https://docs.stripe.com/get-started/account/statement-descriptors#static)to form the complete statement descriptor that appears on the customer’s statement.

### More parameters

- amount_
detailsobject - application_
fee_ amountintegerConnect only - capture_
methodenumsecret key only - excluded_
payment_ method_ typesarray of enums - hooksobject
- payment_
detailsobject - payment_
method_ configurationstring - payment_
method_ dataobject - payment_
method_ optionsobject - payment_
method_ typesarray of strings - transfer_
dataobjectConnect only - transfer_
groupstringConnect only

### Returns

Returns a PaymentIntent object.

`{ "id": "pi_3MtwBwLkdIwHu7ix28a3tqPa", "object": "payment_intent", "amount": 2000, "amount_capturable": 0, "amount_details": { "tip": {} }, "amount_received": 0, "application": null, "application_fee_amount": null, "automatic_payment_methods": { "enabled": true }, "canceled_at": null, "cancellation_reason": null, "capture_method": "automatic", "client_secret": "pi_3MtwBwLkdIwHu7ix28a3tqPa_secret_YrKJUKribcBjcG8HVhfZluoGH", "confirmation_method": "automatic", "created": 1680800504, "currency": "usd", "customer": null, "description": null, "last_payment_error": null, "latest_charge": null, "livemode": false, "metadata": { "order_id": "6735" }, "next_action": null, "on_behalf_of": null, "payment_method": null, "payment_method_options": { "card": { "installments": null, "mandate_options": null, "network": null, "request_three_d_secure": "automatic" }, "link": { "persistent_token": null } }, "payment_method_types": [ "card", "link" ], "processing": null, "receipt_email": null, "review": null, "setup_future_usage": null, "shipping": null, "source": null, "statement_descriptor": null, "statement_descriptor_suffix": null, "status": "requires_payment_method", "transfer_data": null, "transfer_group": null}`


Retrieves the details of a PaymentIntent that has previously been created.

You can retrieve a PaymentIntent client-side using a publishable key when the `client_`

is in the query string.

If you retrieve a PaymentIntent with a publishable key, it only returns a subset of properties. Refer to the [payment intent](https://stripe.com#payment_intent_object) object reference for more details.

### Parameters

- client_
secretstringRequired if you use a publishable key. The client secret of the PaymentIntent. We require it if you use a publishable key to retrieve the source.


### Returns

Returns a PaymentIntent if a valid identifier was provided.

`{ "id": "pi_3MtwBwLkdIwHu7ix28a3tqPa", "object": "payment_intent", "amount": 2000, "amount_capturable": 0, "amount_details": { "tip": {} }, "amount_received": 0, "application": null, "application_fee_amount": null, "automatic_payment_methods": { "enabled": true }, "canceled_at": null, "cancellation_reason": null, "capture_method": "automatic", "client_secret": "pi_3MtwBwLkdIwHu7ix28a3tqPa_secret_YrKJUKribcBjcG8HVhfZluoGH", "confirmation_method": "automatic", "created": 1680800504, "currency": "usd", "customer": null, "description": null, "last_payment_error": null, "latest_charge": null, "livemode": false, "metadata": {}, "next_action": null, "on_behalf_of": null, "payment_method": null, "payment_method_options": { "card": { "installments": null, "mandate_options": null, "network": null, "request_three_d_secure": "automatic" }, "link": { "persistent_token": null } }, "payment_method_types": [ "card", "link" ], "processing": null, "receipt_email": null, "review": null, "setup_future_usage": null, "shipping": null, "source": null, "statement_descriptor": null, "statement_descriptor_suffix": null, "status": "requires_payment_method", "transfer_data": null, "transfer_group": null}`