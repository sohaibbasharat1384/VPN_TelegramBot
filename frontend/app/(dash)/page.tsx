"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, Spinner } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { faNumber, jalaliDate, toman } from "@/lib/format";
import type { Overview, RevenuePoint } from "@/lib/types";

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <Card>
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className={`mt-2 text-2xl font-bold ${accent ?? ""}`}>{value}</div>
    </Card>
  );
}

export default function OverviewPage() {
  const { data: o, loading } = useFetch<Overview>("/stats/overview");
  const { data: series } = useFetch<RevenuePoint[]>("/stats/revenue-series?days=14");

  if (loading || !o) return <Spinner />;

  const chartData = (series ?? []).map((p) => ({ date: jalaliDate(p.date), total: p.total }));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">نمای کلی</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="کل کاربران" value={faNumber(o.total_users)} />
        <Stat label="کاربران فعال" value={faNumber(o.active_users)} accent="text-success" />
        <Stat label="کاربران امروز" value={faNumber(o.daily_users)} />
        <Stat label="اشتراک‌های فعال" value={faNumber(o.active_subscriptions)} accent="text-primary" />
        <Stat label="درآمد امروز" value={toman(o.revenue_daily)} />
        <Stat label="درآمد هفته" value={toman(o.revenue_weekly)} />
        <Stat label="درآمد ماه" value={toman(o.revenue_monthly)} accent="text-success" />
        <Stat label="مجموع کیف پول‌ها" value={toman(o.wallet_total)} />
      </div>

      <Card>
        <h2 className="mb-4 font-semibold">روند درآمد (۱۴ روز اخیر)</h2>
        <div className="h-72" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={70} />
              <Tooltip
                formatter={(v: number) => toman(v)}
                contentStyle={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="hsl(var(--primary))"
                fill="url(#rev)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
