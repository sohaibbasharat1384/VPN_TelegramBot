# Database Design

PostgreSQL 16. All money is stored as **integer Toman** (`BIGINT`). All
timestamps are `TIMESTAMPTZ` (UTC at rest; rendered in `Asia/Tehran`). Primary
keys are `BIGINT` identity unless noted. Soft-delete via `is_deleted` only where
auditing requires retention; otherwise hard delete.

## 1. Entity-Relationship Diagram

```
                          ┌────────────────┐
                          │   admin_users  │
                          └──────┬─────────┘
                                 │ role_id
                          ┌──────▼─────────┐      ┌──────────────────┐
                          │     roles      │◀────▶│ role_permissions │
                          └────────────────┘      └────────┬─────────┘
                                                           │
                                                  ┌────────▼─────────┐
                                                  │   permissions    │
                                                  └──────────────────┘

   ┌──────────┐ 1     1 ┌──────────┐ 1   * ┌──────────────────────┐
   │  users   │─────────│  wallets │───────│ wallet_transactions  │
   └────┬─────┘         └──────────┘       └──────────────────────┘
        │ 1
        │                ┌──────────┐ *   1 ┌──────────┐
        ├───────────────▶│  orders  │───────│  plans   │
        │ *              └────┬─────┘       └────┬─────┘
        │                     │ 1                │ 1
        │                     │ 1               *│
        │ 1            ┌───────▼────────┐  ┌──────▼───────┐
        ├─────────────│  subscriptions │  │   configs    │ (manual inventory)
        │ *           └───────┬────────┘  └──────────────┘
        │                     │ 0..1  config_id (when sold from inventory)
        │              ┌──────▼────────┐
        │              │   payments    │──┐ (1:1 with order; gateway or manual)
        │ *            └───────────────┘  │
        ├───────────────────────────────┐│
        │                ┌──────────────┐││
        ├───────────────▶│   tickets    │││ 1   * ┌──────────────────┐
        │ *              └──────┬───────┘└┴───────│  ticket_messages │
        │                       │ 1               └──────────────────┘
        │ referrer/referred     │
        ├──────────┐    ┌───────▼────────┐
        │          └───▶│   referrals    │──▶ referral_rewards (wallet credit)
        │ *             └────────────────┘
        │        ┌──────────────┐ *   * ┌──────────────────────┐
        ├───────▶│   coupons    │───────│ coupon_redemptions   │
        │        └──────────────┘       └──────────────────────┘
        │
        │        ┌──────────────┐   ┌──────────────┐   ┌────────────────┐
        └───────▶│ broadcasts   │   │ audit_logs   │   │ notifications  │
                 └──────────────┘   └──────────────┘   └────────────────┘

   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │  settings    │   │ payment_cards│   │ panels (Marzban/  │
   │ (key/value)  │   │ (card2card)  │   │  X-UI configs)    │
   └──────────────┘   └──────────────┘   └──────────────────┘
```

## 2. Tables

### `admin_users` — dashboard/admin-bot staff
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| email | CITEXT UNIQUE | login identity (web) |
| telegram_id | BIGINT UNIQUE NULL | links staff to admin bot |
| full_name | TEXT | |
| hashed_password | TEXT | bcrypt; NULL if telegram-only |
| role_id | BIGINT FK → roles | |
| is_active | BOOL default true | |
| last_login_at | TIMESTAMPTZ NULL | |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: `email`, `telegram_id`, `role_id`.

### `roles`, `permissions`, `role_permissions` — RBAC
- `roles`: `id`, `name` (UNIQUE: `super_admin`/`admin`/`support`/`accountant`),
  `description`, `is_system` (protect seeded roles from deletion).
- `permissions`: `id`, `code` (UNIQUE, e.g. `payments.approve`,
  `users.ban`, `coupons.manage`), `description`.
- `role_permissions`: composite PK (`role_id`, `permission_id`).

### `users` — Telegram customers
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| telegram_id | BIGINT UNIQUE NOT NULL | |
| username | TEXT NULL | |
| first_name / last_name | TEXT NULL | |
| language_code | TEXT default 'fa' | |
| phone | TEXT NULL | |
| is_banned | BOOL default false | |
| banned_reason | TEXT NULL | |
| referral_code | TEXT UNIQUE NOT NULL | short code for invite link |
| referred_by_id | BIGINT FK → users NULL | who invited them |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: `telegram_id` (unique), `referral_code` (unique), `referred_by_id`.

### `wallets` / `wallet_transactions`
- `wallets`: `id`, `user_id` UNIQUE FK, `balance` BIGINT default 0
  (CHECK `balance >= 0`), `updated_at`.
- `wallet_transactions`: `id`, `wallet_id` FK, `amount` BIGINT (signed:
  positive = credit, negative = debit), `balance_after` BIGINT, `type`
  (enum: `topup`, `purchase`, `refund`, `referral_reward`, `admin_adjust`),
  `reference_type` / `reference_id` (polymorphic link to order/payment/referral),
  `description`, `created_at`. Index on (`wallet_id`, `created_at`).

### `plans` — sellable subscription plans
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| title | TEXT | e.g. «۵ گیگ / ۳۰ روز» |
| data_limit_gb | INT | 1/2/3/5/10/15 |
| duration_days | INT | 30 |
| price | BIGINT | Toman, editable from admin |
| fulfilment_mode | enum (`manual`,`panel`) | which strategy |
| panel_id | BIGINT FK → panels NULL | required if mode=panel |
| is_active | BOOL default true | |
| sort_order | INT default 0 | |
| created_at / updated_at | TIMESTAMPTZ | |

### `configs` — manual inventory (ready-to-sell)
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| plan_id | BIGINT FK → plans | which category/size |
| subscription_url | TEXT | |
| raw_config | TEXT | vless/vmess/… URI |
| remark | TEXT NULL | |
| status | enum (`available`,`reserved`,`sold`) default available | |
| reserved_until | TIMESTAMPTZ NULL | reservation TTL for pending orders |
| reserved_order_id | BIGINT NULL | |
| sold_to_user_id | BIGINT FK → users NULL | |
| sold_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |

Indexes: (`plan_id`, `status`) — drives "remaining inventory" counts and
`FOR UPDATE SKIP LOCKED` reservation; `status`.

### `orders`
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| user_id | BIGINT FK → users | |
| plan_id | BIGINT FK → plans | |
| kind | enum (`new`,`renewal`) | |
| renew_subscription_id | BIGINT FK → subscriptions NULL | |
| original_price | BIGINT | |
| coupon_id | BIGINT FK → coupons NULL | |
| discount_amount | BIGINT default 0 | |
| final_price | BIGINT | original − discount |
| status | enum (`pending`,`awaiting_payment`,`paid`,`delivered`,`cancelled`,`expired`) | |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: (`user_id`,`status`), `status`, `created_at`.

### `subscriptions`
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| user_id | BIGINT FK → users | |
| plan_id | BIGINT FK → plans | |
| order_id | BIGINT FK → orders | origin order |
| config_id | BIGINT FK → configs NULL | set when fulfilled from inventory |
| panel_id | BIGINT FK → panels NULL | set when fulfilled via panel |
| panel_username | TEXT NULL | identity on the panel |
| subscription_url | TEXT | delivered link |
| data_limit_bytes | BIGINT | |
| data_used_bytes | BIGINT default 0 | synced from panel |
| starts_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | |
| status | enum (`active`,`expired`,`disabled`) | |
| usage_alert_level | SMALLINT default 0 | last sent: 0/80/90/100 |
| expiry_alerts_sent | TEXT[] default '{}' | which of 7/3/1/expired sent |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: (`user_id`,`status`), `expires_at`, `status`, `panel_id`.

### `payments`
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| user_id | BIGINT FK → users | |
| order_id | BIGINT FK → orders NULL | NULL when it's a wallet top-up |
| purpose | enum (`order`,`wallet_topup`) | |
| method | enum (`wallet`,`card_to_card`,`gateway`) | |
| provider | TEXT NULL | zarinpal/idpay/nextpay |
| amount | BIGINT | |
| status | enum (`pending`,`approved`,`rejected`,`failed`) | |
| card_id | BIGINT FK → payment_cards NULL | card2card target |
| receipt_path | TEXT NULL | uploaded receipt file |
| tracking_number | TEXT NULL | card2card ref |
| gateway_authority | TEXT NULL | gateway transaction id |
| gateway_ref_id | TEXT NULL | settlement ref |
| reviewed_by_id | BIGINT FK → admin_users NULL | |
| admin_note | TEXT NULL | |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: (`status`,`created_at`), `user_id`, `gateway_authority`.

### `payment_cards` — card-to-card destinations (editable)
`id`, `card_number`, `card_holder`, `bank_name`, `is_active`, `sort_order`,
timestamps.

### `coupons` / `coupon_redemptions`
- `coupons`: `id`, `code` UNIQUE, `discount_type` (enum `percent`/`fixed`),
  `discount_value` BIGINT, `max_uses` INT NULL, `used_count` INT default 0,
  `per_user_limit` INT default 1, `min_order_amount` BIGINT default 0,
  `expires_at` TIMESTAMPTZ NULL, `is_active` BOOL, timestamps.
- `coupon_redemptions`: `id`, `coupon_id` FK, `user_id` FK, `order_id` FK,
  `discount_amount`, `created_at`. UNIQUE per-user enforcement via index
  (`coupon_id`,`user_id`) checked against `per_user_limit` in service.

### `referrals` / `referral_rewards`
- `referrals`: `id`, `referrer_id` FK→users, `referred_id` FK→users UNIQUE,
  `status` (enum `pending`/`qualified`/`rewarded`), `created_at`.
- `referral_rewards`: `id`, `referral_id` FK, `referrer_id` FK, `amount` BIGINT,
  `wallet_transaction_id` FK NULL, `created_at`.

Referral reward amount/threshold are stored in `settings`.

### `tickets` / `ticket_messages`
- `tickets`: `id`, `user_id` FK, `subject`, `status` (enum
  `open`/`pending`/`answered`/`closed`), `priority`, `assigned_admin_id` FK NULL,
  `last_message_at`, timestamps. Index (`status`,`last_message_at`).
- `ticket_messages`: `id`, `ticket_id` FK, `sender_type` (enum `user`/`admin`),
  `sender_user_id` NULL, `sender_admin_id` NULL, `body`, `attachment_path` NULL,
  `created_at`.

### `broadcasts`
`id`, `admin_id` FK, `content_type` (text/photo/video/file), `body`,
`media_path` NULL, `target` (enum `all`/`active`/`specific`),
`target_user_ids` BIGINT[] NULL, `status` (queued/sending/done/failed),
`sent_count`, `failed_count`, `created_at`.

### `audit_logs`
| column | type | notes |
|--------|------|-------|
| id | BIGINT PK | |
| actor_type | enum (`admin`,`system`,`user`) | |
| actor_id | BIGINT NULL | |
| action | TEXT | e.g. `payment.approve` |
| target_type | TEXT NULL | e.g. `payment` |
| target_id | BIGINT NULL | |
| ip_address | INET NULL | |
| old_value | JSONB NULL | |
| new_value | JSONB NULL | |
| created_at | TIMESTAMPTZ | |

Indexes: (`actor_id`,`created_at`), (`target_type`,`target_id`), `action`.

### `notifications` — outbound message log (dedupe & audit)
`id`, `user_id` FK, `kind` (enum: `usage_80`/`usage_90`/`usage_100`/`expiry_7`/
`expiry_3`/`expiry_1`/`expired`/`low_inventory`/`generic`), `payload` JSONB,
`sent_at` TIMESTAMPTZ NULL, `created_at`. UNIQUE (`user_id`,`kind`,`reference_id`)
prevents duplicate alerts.

### `panels` — integration endpoints
`id`, `name`, `type` (enum `marzban`/`xui`), `base_url`, `username`,
`password_enc` (encrypted), `is_active`, `extra` JSONB (inbound/flow templates),
timestamps.

### `settings` — key/value app config (editable from dashboard)
`key` TEXT PK, `value` JSONB, `updated_by_id` FK NULL, `updated_at`. Seeded keys:
`referral_reward_amount`, `referral_threshold`, `low_inventory_threshold`,
`card_to_card_enabled`, `gateway_enabled`.

### `refresh_tokens` — rotating refresh-token store
`id`, `admin_user_id` FK, `token_hash` (sha256), `expires_at`, `revoked_at` NULL,
`replaced_by_id` NULL, `user_agent`, `ip_address` INET, `created_at`. Index on
`token_hash`, `admin_user_id`.

## 3. Key constraints & integrity rules

- `wallets.balance >= 0` (CHECK) — no negative balances; debits validated in
  service layer inside a transaction.
- `orders.final_price = original_price - discount_amount` enforced in service.
- A `config` can be sold once: partial unique behaviour via `status` + the
  reservation/locking flow (`FOR UPDATE SKIP LOCKED`).
- `referrals.referred_id` UNIQUE — a user can be referred only once.
- `subscriptions` must have exactly one fulfilment source: CHECK
  `(config_id IS NOT NULL) <> (panel_id IS NOT NULL)`.
- All FKs use `ON DELETE RESTRICT` except logs/messages which cascade with parent.

## 4. Migrations

Schema is managed by **Alembic** (`backend/alembic/`). The initial migration
creates all enums + tables + indexes; a data migration seeds roles, permissions,
default settings, and the bootstrap super admin(s) from `BOOTSTRAP_SUPER_ADMINS`.
