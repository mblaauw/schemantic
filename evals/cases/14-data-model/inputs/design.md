# Seed bank: what we store (fictional)

We keep our records in one database, except germination tests, which the partner lab holds in its own system.

## Variety
A variety has a `variety_id` (uuid, primary key) and a `latin_name`, which must be unique. We also keep a `common_name`.

## Batch
Each harvest of a variety gets one batch. A batch has a `batch_id` (uuid, primary key), a `variety_id` pointing at its
variety, a `harvested_on` date and a `grams` amount. A variety has many batches over the years.

## Member
A member has a `member_id` (uuid, primary key) and an `email`.

## Request
A member places requests. A request has a `request_id` (uuid, primary key), a `member_id` and a `batch_id`, and a `status`.
A member can place many requests. Each request is for one batch; one batch can serve many requests.

## Germination test
The lab tests batches and reports a `sprouted_percent` with a `tested_on` date. We have not settled whether a batch is
tested once or every year, so we do not yet know how many tests a batch can have.
