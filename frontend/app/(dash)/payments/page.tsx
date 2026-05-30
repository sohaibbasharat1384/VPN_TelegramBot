"use client";

import { useState } from "react";
import { Badge, Button, Card, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { jalaliDate, toman } from "@/lib/format";
import type { Page, Payment } from "@/lib/types";

const STATUS = [
  { key: "pending", label: "در انتظار" },
  { key: "approved", label: "تأییدشده" },
  { key: "rejected", label: "ردشده" },
];

const PURPOSE: Record<string, string> = { order: "خرید", wallet_topup: "شارژ کیف پول" };
const METHOD: Record<string, string> = { wallet: "کیف پول", card_to_card: "کارت‌به‌کارت", gateway: "درگاه" };

export default function PaymentsPage() {
  const [status, setStatus] = useState("pending");
  const [busy, setBusy] = useState<number | null>(null);
  const { data, loading, reload } = useFetch<Page<Payment>>(`/payments?status=${status}&pageSize=50`);

  async function review(id: number, action: "approve" | "reject") {
    setBusy(id);
    try {
      await api.post(`/payments/${id}/${action}`, {});
      reload();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">تراکنش‌ها</h1>
      <div className="flex gap-2">
        {STATUS.map((s) => (
          <Button
            key={s.key}
            variant={status === s.key ? "primary" : "outline"}
            onClick={() => setStatus(s.key)}
          >
            {s.label}
          </Button>
        ))}
      </div>

      {loading ? (
        <Spinner />
      ) : !data || data.items.length === 0 ? (
        <Card>تراکنشی یافت نشد.</Card>
      ) : (
        <Table
          head={
            <tr>
              <Th>شناسه</Th>
              <Th>کاربر</Th>
              <Th>نوع</Th>
              <Th>روش</Th>
              <Th>مبلغ</Th>
              <Th>پیگیری</Th>
              <Th>تاریخ</Th>
              <Th>عملیات</Th>
            </tr>
          }
        >
          {data.items.map((p) => (
            <tr key={p.id}>
              <Td>#{p.id}</Td>
              <Td>{p.userId}</Td>
              <Td>{PURPOSE[p.purpose] ?? p.purpose}</Td>
              <Td>{METHOD[p.method] ?? p.method}</Td>
              <Td>{toman(p.amount)}</Td>
              <Td>{p.trackingNumber ?? "—"}</Td>
              <Td>{jalaliDate(p.createdAt)}</Td>
              <Td>
                {p.status === "pending" ? (
                  <div className="flex gap-2">
                    <Button
                      variant="success"
                      disabled={busy === p.id}
                      onClick={() => review(p.id, "approve")}
                    >
                      تأیید
                    </Button>
                    <Button
                      variant="danger"
                      disabled={busy === p.id}
                      onClick={() => review(p.id, "reject")}
                    >
                      رد
                    </Button>
                  </div>
                ) : (
                  <Badge tone={p.status === "approved" ? "success" : "danger"}>
                    {p.status === "approved" ? "تأییدشده" : "ردشده"}
                  </Badge>
                )}
              </Td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
