"use client";

import { useEffect, useState } from "react";
import { Button, Card, Input, Spinner } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";

const LABELS: Record<string, string> = {
  referral_reward_amount: "پاداش معرفی (تومان)",
  referral_threshold: "آستانه پاداش معرفی",
  low_inventory_threshold: "آستانه هشدار موجودی",
  card_to_card_enabled: "فعال‌سازی کارت‌به‌کارت",
  gateway_enabled: "فعال‌سازی درگاه پرداخت",
};

export default function SettingsPage() {
  const { data, loading } = useFetch<Record<string, unknown>>("/settings");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      const v: Record<string, string> = {};
      for (const [k, val] of Object.entries(data)) v[k] = String(val);
      setValues(v);
    }
  }, [data]);

  async function save(key: string) {
    const raw = values[key];
    let value: unknown = raw;
    if (raw === "true" || raw === "false") value = raw === "true";
    else if (/^\d+$/.test(raw)) value = parseInt(raw, 10);
    await api.put("/settings", { key, value });
    setSaved(key);
    setTimeout(() => setSaved(null), 1500);
  }

  if (loading || !data) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">تنظیمات</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Object.keys(data).map((key) => (
          <Card key={key} className="space-y-2">
            <label className="block text-sm font-medium">{LABELS[key] ?? key}</label>
            <div className="flex gap-2">
              <Input
                dir="ltr"
                value={values[key] ?? ""}
                onChange={(e) => setValues({ ...values, [key]: e.target.value })}
              />
              <Button onClick={() => save(key)}>{saved === key ? "✓" : "ذخیره"}</Button>
            </div>
            <p className="text-xs text-muted-foreground">{key}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
