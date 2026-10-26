# Proposal: one notification service (fictional)

Today each of the five product teams sends its own e-mails and push messages. We propose one notification service:
teams publish a notification request; the service picks the channel (e-mail, push, SMS) from the customer's
preferences in the preference centre and sends it through the channel providers.

Decided: templates live in one template store, owned by the brand team. Decided: every message is logged for 90 days.

Not decided:
1. Do we buy a notification platform or build the service ourselves?
2. Do teams call the service synchronously (REST) or publish to the event bus?
