"use client";

import { useState } from "react";
import { Badge, Button, Card, Input, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { faNumber } from "@/lib/format";
import type { InventoryCount } from "@/lib/types";

export default function InventoryPage() {
  const { can } = useAuth();
  const { data, loading, reload } = useFetch<InventoryCount[]>("/inventory/counts");
  const [planId, setPlanId] = useState<number | null>(null);
  const [url, setUrl] = useState("");
  const [raw, setRaw] = useState("");
  const [saving, setSaving] = useState(false);

  async function addConfig() {
    if (!planId || !url || !raw) return;
    setSaving(true);
    try {
      await api.post("/inventory/configs", { planId, subscriptionUrl: url, rawConfig: raw });
      setUrl("");
      setRaw("");
      reload();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">انبار کانفیگ‌ها</h1>

      {loading || !data ? (
        <Spinner />
      ) : (
        <Table
          head={
            <tr>
              <Th>پلن</Th>
              <Th>آماده فروش</Th>
              <Th>رزرو</Th>
              <Th>فروخته‌شده</Th>
              <Th>وضعیت</Th>
            </tr>
          }
        >
          {data.map((c) => (
            <tr key={c.planId}>
              <Td>{c.title}</Td>
              <Td>{faNumber(c.available)}</Td>
              <Td>{faNumber(c.reserved)}</Td>
              <Td>{faNumber(c.sold)}</Td>
              <Td>
                {c.low ? <Badge tone="danger">کم‌موجودی</Badge> : <Badge tone="success">کافی</Badge>}
              </Td>
            </tr>
          ))}
        </Table>
      )}

      {can("inventory.manage") && data && (
        <Card className="space-y-3">
          <h2 className="font-semibold">افزودن کانفیگ به انبار</h2>
          <select
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
            value={planId ?? ""}
            onChange={(e) => setPlanId(Number(e.target.value))}
          >
            <option value="">انتخاب پلن…</option>
            {data.map((c) => (
              <option key={c.planId} value={c.planId}>
                {c.title}
              </option>
            ))}
          </select>
          <Input placeholder="Subscription URL" dir="ltr" value={url} onChange={(e) => setUrl(e.target.value)} />
          <Input placeholder="Raw config" dir="ltr" value={raw} onChange={(e) => setRaw(e.target.value)} />
          <Button onClick={addConfig} disabled={saving || !planId}>
            {saving ? "در حال افزودن…" : "افزودن"}
          </Button>
        </Card>
      )}
    </div>
  );
}
