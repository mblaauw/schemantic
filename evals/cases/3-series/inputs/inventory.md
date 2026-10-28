# Platform inventory (fictional)

Every component, by area, with what it does.

## Customer channels

- Web shop: part of customer channels.
- Mobile app: part of customer channels.
- Store kiosks: part of customer channels.
- Call centre: part of customer channels.
- Partner API: part of customer channels.

## Identity

- Login service: part of identity.
- Customer profiles: part of identity.
- Consent registry: part of identity.
- Fraud scoring: part of identity.

## Commerce

- Catalog: part of commerce.
- Pricing: part of commerce.
- Promotions: part of commerce.
- Cart: part of commerce.
- Checkout: part of commerce.
- Orders: part of commerce.

## Payments

- Payment gateway: part of payments.
- Refunds: part of payments.
- Invoicing: part of payments.
- Ledger: part of payments.

## Fulfilment

- Warehouse management: part of fulfilment.
- Picking app: part of fulfilment.
- Carrier integration: part of fulfilment.
- Returns: part of fulfilment.

## Customer service

- Ticketing: part of customer service.
- Knowledge base: part of customer service.
- Chatbot: part of customer service.

## Data

- Event bus: part of data.
- Lakehouse: part of data.
- Reporting: part of data.
- Forecasting: part of data.

## Platform

- Kubernetes clusters: part of platform.
- CI/CD: part of platform.
- Observability: part of platform.
- Secrets: part of platform.

## Back office

- HR system: part of back office.
- Finance system: part of back office.
- Procurement: part of back office.

Flows: channels call identity and commerce; commerce calls payments and fulfilment; everything publishes events to the event bus; data reads from the bus; customer service reads orders and profiles.
