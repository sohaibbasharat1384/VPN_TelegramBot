"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CreditCard,
  Users,
  Package,
  Tag,
  Ticket,
  Boxes,
  Settings,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "نمای کلی", icon: LayoutDashboard, perm: "dashboard.view" },
  { href: "/payments", label: "تراکنش‌ها", icon: CreditCard, perm: "payments.view" },
  { href: "/users", label: "کاربران", icon: Users, perm: "users.view" },
  { href: "/inventory", label: "انبار", icon: Boxes, perm: "inventory.view" },
  { href: "/plans", label: "پلن‌ها و قیمت‌ها", icon: Package, perm: "plans.manage" },
  { href: "/coupons", label: "کدهای تخفیف", icon: Tag, perm: "coupons.manage" },
  { href: "/tickets", label: "تیکت‌ها", icon: Ticket, perm: "tickets.view" },
  { href: "/settings", label: "تنظیمات", icon: Settings, perm: "settings.manage" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { can, logout, profile } = useAuth();

  return (
    <aside className="flex h-screen w-64 flex-col border-l border-border bg-card">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5 text-lg font-bold">
        🛡️ VPN Robot
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV.filter((item) => can(item.perm)).map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition",
                active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
              )}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <div className="mb-2 px-2 text-xs text-muted-foreground">
          {profile?.fullName} — {profile?.role}
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm text-danger hover:bg-muted"
        >
          <LogOut size={18} />
          خروج
        </button>
      </div>
    </aside>
  );
}
