"use client";

import { useState } from "react";
import { Badge, Button, Card, Input, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { faNumber, toman } from "@/lib/format";
import type { Coupon } from "@/lib/types";

export default function CouponsPage() {
  const { data, loading, reload } = useFetch<Coupon[]>("/coupons");
  const [code, setCode] = useState("");
  const [type, setType] = useState<"percent" | "fixed">("percent");
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);

  async function create() {
    const v = parseInt(value, 10);
    if (!code || Number.isNaN(v)) return;
    setSaving(true);
    try {
      await api.post("/coupons", { code, discountType: type, discountValue: v });
      setCode("");
      setValue("");
      reload();
    } finally {
      setSaving(false);
    }
  }

  async function toggle(c: Coupon) {
    await api.post(`/coupons/${c.id}/toggle`, {});
    reload();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">کدهای تخفیف</h1>

      <Card className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
        <div>
          <label className="mb-1 block text-sm">کد</label>
          <Input dir="ltr" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} />
        </div>
        <div>
          <label className="mb-1 block text-sm">نوع</label>
          <select
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value as "percent" | "fixed")}
          >
            <option value="percent">درصدی</option>
            <option value="fixed">مبلغی (تومان)</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm">مقدار</label>
          <Input dir="ltr" value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <Button onClick={create} disabled={saving}>
          ساخت کد
        </Button>
      </Card>

      {loading || !data ? (
        <Spinner />
      ) : (
        <Table
          head={
            <tr>
              <Th>کد</Th>
              <Th>تخفیف</Th>
              <Th>استفاده</Th>
              <Th>وضعیت</Th>
              <Th>عملیات</Th>
            </tr>
          }
        >
          {data.map((c) => (
            <tr key={c.id}>
              <Td>{c.code}</Td>
              <Td>{c.discountType === "percent" ? `${faNumber(c.discountValue)}٪` : toman(c.discountValue)}</Td>
              <Td>{faNumber(c.usedCount)}</Td>
              <Td>
                <Badge tone={c.isActive ? "success" : "muted"}>{c.isActive ? "فعال" : "غیرفعال"}</Badge>
              </Td>
              <Td>
                <Button variant="outline" onClick={() => toggle(c)}>
                  {c.isActive ? "غیرفعال" : "فعال"}
                </Button>
              </Td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
