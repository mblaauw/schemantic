# How a card payment works (fictional, from the payments wiki)

The mobile app sends the payment to the payment API. The payment API asks fraud check whether the payment looks fine;
fraud check answers with a score. If the score is fine, the payment API asks the bank gateway to authorise the amount.
The bank gateway calls the bank and returns approved or declined. On approved, the payment API books the amount in the
ledger, which confirms the booking. Only then does the payment API tell the app the payment succeeded.

Declines go straight back to the app; we do not book anything. Nobody has decided yet whether fraud check may be skipped
below 10 euro.
