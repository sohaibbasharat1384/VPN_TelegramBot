"use client";

import { useState } from "react";
import { Badge, Button, Card, Input, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { jalaliDate } from "@/lib/format";
import type { Page, Ticket, TicketDetail } from "@/lib/types";

const STATUS_FA: Record<string, string> = {
  open: "باز",
  pending: "در انتظار",
  answered: "پاسخ‌داده‌شده",
  closed: "بسته",
};

export default function TicketsPage() {
  const { data, loading, reload } = useFetch<Page<Ticket>>("/tickets?pageSize=50");
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">تیکت‌ها</h1>
        {loading || !data ? (
          <Spinner />
        ) : (
          <Table
            head={
              <tr>
                <Th>#</Th>
                <Th>موضوع</Th>
                <Th>وضعیت</Th>
                <Th>آخرین پیام</Th>
              </tr>
            }
          >
            {data.items.map((t) => (
              <tr key={t.id} className="cursor-pointer hover:bg-muted/40" onClick={() => setOpenId(t.id)}>
                <Td>#{t.id}</Td>
                <Td>{t.subject}</Td>
                <Td>
                  <Badge tone={t.status === "closed" ? "muted" : "primary"}>
                    {STATUS_FA[t.status] ?? t.status}
                  </Badge>
                </Td>
                <Td>{jalaliDate(t.lastMessageAt)}</Td>
              </tr>
            ))}
          </Table>
        )}
      </div>
      {openId !== null && <TicketThread id={openId} onChange={reload} />}
    </div>
  );
}

function TicketThread({ id, onChange }: { id: number; onChange: () => void }) {
  const { data, loading, reload } = useFetch<TicketDetail>(`/tickets/${id}`);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!body.trim()) return;
    setBusy(true);
    try {
      await api.post(`/tickets/${id}/reply`, { body });
      setBody("");
      reload();
      onChange();
    } finally {
      setBusy(false);
    }
  }

  async function close() {
    await api.post(`/tickets/${id}/status`, { status: "closed" });
    reload();
    onChange();
  }

  if (loading || !data) return <Spinner />;

  return (
    <Card className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">
          تیکت #{data.id} — {data.subject}
        </h2>
        <Button variant="outline" onClick={close}>
          بستن تیکت
        </Button>
      </div>
      <div className="mb-4 max-h-80 space-y-2 overflow-y-auto">
        {data.messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-md p-2 text-sm ${
              m.senderType === "admin" ? "bg-primary/10" : "bg-muted"
            }`}
          >
            <div className="mb-1 text-xs text-muted-foreground">
              {m.senderType === "admin" ? "پشتیبانی" : "کاربر"} — {jalaliDate(m.createdAt)}
            </div>
            {m.body}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Input placeholder="پاسخ شما…" value={body} onChange={(e) => setBody(e.target.value)} />
        <Button onClick={send} disabled={busy}>
          ارسال
        </Button>
      </div>
    </Card>
  );
}
