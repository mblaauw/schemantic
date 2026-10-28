# Bookings service (fictional)

Lets customers book appointments. The `web` app is the customer front end; the `api` handles bookings and
availability; the `notifier` sends confirmation e-mails and SMS through an external messaging provider.
Calendars of the clinics are read every five minutes from their scheduling system (an external API).
