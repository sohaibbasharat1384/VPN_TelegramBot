export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface AdminProfile {
  id: number;
  email: string | null;
  telegramId: number | null;
  fullName: string;
  role: string;
  permissions: string[];
  isActive: boolean;
}

export interface Overview {
  total_users: number;
  active_users: number;
  daily_users: number;
  active_subscriptions: number;
  revenue_daily: number;
  revenue_weekly: number;
  revenue_monthly: number;
  wallet_total: number;
  referral_total: number;
}

export interface RevenuePoint {
  date: string;
  total: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UserRow {
  id: number;
  telegramId: number;
  username: string | null;
  firstName: string | null;
  lastName: string | null;
  isBanned: boolean;
  referralCode: string;
  createdAt: string;
}

export interface Payment {
  id: number;
  userId: number;
  orderId: number | null;
  purpose: string;
  method: string;
  provider: string | null;
  amount: number;
  status: string;
  trackingNumber: string | null;
  createdAt: string;
}

export interface Plan {
  id: number;
  title: string;
  dataLimitGb: number;
  durationDays: number;
  price: number;
  fulfilmentMode: string;
  panelId: number | null;
  isActive: boolean;
  sortOrder: number;
}

export interface InventoryCount {
  planId: number;
  title: string;
  available: number;
  reserved: number;
  sold: number;
  low: boolean;
}

export interface Coupon {
  id: number;
  code: string;
  discountType: string;
  discountValue: number;
  maxUses: number | null;
  usedCount: number;
  perUserLimit: number;
  minOrderAmount: number;
  expiresAt: string | null;
  isActive: boolean;
}

export interface Ticket {
  id: number;
  userId: number;
  subject: string;
  status: string;
  lastMessageAt: string;
  createdAt: string;
}

export interface TicketMessage {
  id: number;
  senderType: string;
  body: string;
  attachmentPath: string | null;
  createdAt: string;
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[];
}
