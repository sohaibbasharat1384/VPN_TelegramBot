"use client";

import { useState } from "react";
import { Badge, Button, Card, Input, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { faNumber, toman } from "@/lib/format";
import type { Plan } from "@/lib/types";

export default function PlansPage() {
  const { data, loading, reload } = useFetch<Plan[]>("/plans");
  const [edit, setEdit] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);

  async function savePrice(plan: Plan) {
    const value = parseInt(edit[plan.id] ?? "", 10);
    if (Number.isNaN(value)) return;
    setBusy(plan.id);
    try {
      await api.patch(`/plans/${plan.id}`, { price: value });
      reload();
    } finally {
      setBusy(null);
    }
  }

  async function toggle(plan: Plan) {
    setBusy(plan.id);
    try {
      await api.patch(`/plans/${plan.id}`, { isActive: !plan.isActive });
      reload();
    } finally {
      setBusy(null);
    }
  }

  if (loading || !data) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">پلن‌ها و قیمت‌ها</h1>
      <Table
        head={
          <tr>
            <Th>عنوان</Th>
            <Th>حجم</Th>
            <Th>مدت</Th>
            <Th>قیمت فعلی</Th>
            <Th>قیمت جدید</Th>
            <Th>وضعیت</Th>
            <Th>عملیات</Th>
          </tr>
        }
      >
        {data.map((p) => (
          <tr key={p.id}>
            <Td>{p.title}</Td>
            <Td>{faNumber(p.dataLimitGb)} گیگ</Td>
            <Td>{faNumber(p.durationDays)} روز</Td>
            <Td>{toman(p.price)}</Td>
            <Td className="w-40">
              <Input
                dir="ltr"
                placeholder={String(p.price)}
                value={edit[p.id] ?? ""}
                onChange={(e) => setEdit({ ...edit, [p.id]: e.target.value })}
              />
            </Td>
            <Td>
              <Badge tone={p.isActive ? "success" : "muted"}>{p.isActive ? "فعال" : "غیرفعال"}</Badge>
            </Td>
            <Td>
              <div className="flex gap-2">
                <Button disabled={busy === p.id} onClick={() => savePrice(p)}>
                  ذخیره
                </Button>
                <Button variant="outline" disabled={busy === p.id} onClick={() => toggle(p)}>
                  {p.isActive ? "غیرفعال‌سازی" : "فعال‌سازی"}
                </Button>
              </div>
            </Td>
          </tr>
        ))}
      </Table>
    </div>
  );
}
