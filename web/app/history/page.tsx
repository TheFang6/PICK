"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { getMe } from "@/lib/auth";
import { Nav } from "@/components/pick/nav";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface HistoryEntry {
  id: string;
  restaurant_id: string;
  restaurant_name: string;
  date: string;
  attendees: string[];
  attendee_names: string[];
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function HistoryPage() {
  const [tab, setTab] = useState<"self" | "team">("self");
  const [month, setMonth] = useState(currentMonth);

  const [year, mon] = month.split("-").map(Number);

  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getMe });

  const { data, isLoading } = useQuery({
    queryKey: ["history", tab, month],
    queryFn: () => {
      const path =
        tab === "team"
          ? `/history/team?month=${month}`
          : `/history?user_id=${user!.user_id}&month=${month}`;
      return api.get(path).then((r) => r.json());
    },
    enabled: !!user,
  });

  const entries: HistoryEntry[] = data?.entries || [];

  const entryMap = useMemo(() => {
    const map = new Map<number, HistoryEntry[]>();
    for (const entry of entries) {
      const day = parseInt(entry.date.split("-")[2], 10);
      if (!map.has(day)) map.set(day, []);
      map.get(day)!.push(entry);
    }
    return map;
  }, [entries]);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, mon - 1, 1).getDay();
    const daysInMonth = new Date(year, mon, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }, [year, mon]);

  const today = new Date();
  const isToday = (day: number) =>
    day === today.getDate() &&
    mon === today.getMonth() + 1 &&
    year === today.getFullYear();

  const monthLabel = new Date(year, mon - 1).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
  });

  const changeMonth = (delta: number) => {
    const d = new Date(year, mon - 1 + delta, 1);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  };

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 space-y-4">
        <h1 className="text-2xl font-bold">Lunch History</h1>

        {/* Tabs */}
        <div className="flex gap-1 bg-muted rounded-lg p-1">
          {([
            { key: "self" as const, label: "Mine" },
            { key: "team" as const, label: "Team" },
          ]).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                tab === t.key
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Month nav */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="icon" onClick={() => changeMonth(-1)}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <span className="font-semibold">{monthLabel}</span>
          <Button variant="ghost" size="icon" onClick={() => changeMonth(1)}>
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>

        {/* Calendar grid */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-7 bg-muted">
              {WEEKDAYS.map((d) => (
                <div
                  key={d}
                  className="py-2 text-center text-xs font-medium text-muted-foreground"
                >
                  {d}
                </div>
              ))}
            </div>

            {/* Days */}
            <div className="grid grid-cols-7 divide-x divide-y">
              {calendarDays.map((day, i) => {
                const dayEntries = day ? entryMap.get(day) || [] : [];
                return (
                  <div
                    key={i}
                    className={cn(
                      "min-h-[100px] p-1.5",
                      !day && "bg-muted/30",
                    )}
                  >
                    {day && (
                      <>
                        <span
                          className={cn(
                            "inline-flex h-7 w-7 items-center justify-center rounded-full text-sm",
                            isToday(day)
                              ? "bg-primary text-primary-foreground font-bold"
                              : "text-muted-foreground",
                          )}
                        >
                          {day}
                        </span>
                        <div className="mt-1 space-y-1">
                          {dayEntries.map((entry) => (
                            <div
                              key={entry.id}
                              className="rounded-md bg-primary/10 px-1.5 py-1 text-xs leading-snug text-primary font-medium break-words"
                              title={`${entry.restaurant_name} — ${entry.attendee_names.join(", ")}`}
                            >
                              {entry.restaurant_name || "?"}
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
