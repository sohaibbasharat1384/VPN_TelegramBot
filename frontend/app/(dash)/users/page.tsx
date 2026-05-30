"use client";

import { useState } from "react";
import { Badge, Button, Card, Input, Spinner, Table, Td, Th } from "@/components/ui";
import { useFetch } from "@/lib/use-api";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { faNumber, jalaliDate } from "@/lib/format";
import type { Page, UserRow } from "@/lib/types";

export default function UsersPage() {
  const { can } = useAuth();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const { data, loading, reload } = useFetch<Page<UserRow>>(
    `/users?pageSize=50${query ? `&q=${encodeURIComponent(query)}` : ""}`,
  );

  async function toggleBan(u: UserRow) {
    await api.post(`/users/${u.id}/ban`, { banned: !u.isBanned, reason: "از داشبورد" });
    reload();
  }

  async function adjust(u: UserRow) {
    const raw = prompt("مبلغ تغییر موجودی (تومان، مثبت/منفی):");
    if (!raw) return;
    const delta = parseInt(raw, 10);
    if (Number.isNaN(delta)) return;
    await api.post(`/users/${u.id}/wallet/adjust`, { delta, description: "تنظیم از داشبورد" });
    reload();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">کاربران</h1>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q);
        }}
      >
        <Input placeholder="جستجو: شناسه، نام کاربری، کد معرف..." value={q} onChange={(e) => setQ(e.target.value)} />
        <Button type="submit">جستجو</Button>
      </form>

      {loading ? (
        <Spinner />
      ) : !data || data.items.length === 0 ? (
        <Card>کاربری یافت نشد.</Card>
      ) : (
        <Table
          head={
            <tr>
              <Th>شناسه تلگرام</Th>
              <Th>نام</Th>
              <Th>کد معرف</Th>
              <Th>وضعیت</Th>
              <Th>عضویت</Th>
              <Th>عملیات</Th>
            </tr>
          }
        >
          {data.items.map((u) => (
            <tr key={u.id}>
              <Td>{faNumber(u.telegramId)}</Td>
              <Td>{[u.firstName, u.lastName].filter(Boolean).join(" ") || (u.username ?? "—")}</Td>
              <Td>{u.referralCode}</Td>
              <Td>
                <Badge tone={u.isBanned ? "danger" : "success"}>
                  {u.isBanned ? "مسدود" : "فعال"}
                </Badge>
              </Td>
              <Td>{jalaliDate(u.createdAt)}</Td>
              <Td>
                <div className="flex gap-2">
                  {can("users.ban") && (
                    <Button variant={u.isBanned ? "success" : "danger"} onClick={() => toggleBan(u)}>
                      {u.isBanned ? "رفع مسدودی" : "مسدود"}
                    </Button>
                  )}
                  {can("wallet.adjust") && (
                    <Button variant="outline" onClick={() => adjust(u)}>
                      موجودی
                    </Button>
                  )}
                </div>
              </Td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
