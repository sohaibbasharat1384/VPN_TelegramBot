const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export function toFaDigits(input: string | number): string {
  return String(input).replace(/\d/g, (d) => FA_DIGITS[Number(d)]);
}

export function toman(amount: number): string {
  return `${toFaDigits(amount.toLocaleString("en-US"))} تومان`;
}

export function faNumber(n: number): string {
  return toFaDigits(n.toLocaleString("en-US"));
}

export function humanBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${toFaDigits(value.toFixed(value < 10 && i > 0 ? 1 : 0))} ${units[i]}`;
}

export function jalaliDate(iso: string): string {
  try {
    return toFaDigits(
      new Intl.DateTimeFormat("fa-IR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date(iso)),
    );
  } catch {
    return iso;
  }
}
