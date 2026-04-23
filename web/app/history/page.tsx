"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2, UtensilsCrossed, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { getMe } from "@/lib/auth";
import { Nav } from "@/components/pick/nav";
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
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

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
    setSelectedDay(null);
  };

  const selectedEntries = selectedDay ? entryMap.get(selectedDay) || [] : [];
  const selectedDateLabel = selectedDay
    ? new Date(year, mon - 1, selectedDay).toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10 space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
            Lunch{" "}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              History
            </span>
          </h1>
          <p className="mt-1 text-sm text-gray-400">Browse past lunch picks by month</p>
        </div>

        {/* Tabs + month nav */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 rounded-full bg-white/60 p-1 backdrop-blur-sm border border-white/80">
            {(["self", "team"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setSelectedDay(null); }}
                className={cn(
                  "rounded-full px-5 py-1.5 text-sm font-medium transition-all",
                  tab === t
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-indigo-600"
                )}
              >
                {t === "self" ? "Mine" : "Team"}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              aria-label="Previous month"
              onClick={() => changeMonth(-1)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/80 bg-white/70 text-gray-500 hover:bg-white transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="min-w-[130px] text-center text-sm font-bold text-gray-800">
              {monthLabel}
            </span>
            <button
              aria-label="Next month"
              onClick={() => changeMonth(1)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/80 bg-white/70 text-gray-500 hover:bg-white transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* 2-column layout: calendar + detail panel */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
          {/* Calendar */}
          <div className="glass overflow-hidden">
            {/* Weekday headers */}
            <div className="grid grid-cols-7 border-b border-white/60 bg-white/30">
              {WEEKDAYS.map((d) => (
                <div
                  key={d}
                  className="py-2.5 text-center text-xs font-semibold text-gray-400 uppercase tracking-wide"
                >
                  {d}
                </div>
              ))}
            </div>

            {isLoading ? (
              <div className="flex justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
              </div>
            ) : (
              <div className="grid grid-cols-7 divide-x divide-y divide-white/40">
                {calendarDays.map((day, i) => {
                  const dayEntries = day ? entryMap.get(day) || [] : [];
                  const isSelected = day === selectedDay;
                  return (
                    <div
                      key={i}
                      onClick={() => day && setSelectedDay(day === selectedDay ? null : day)}
                      className={cn(
                        "min-h-[90px] p-2 transition-colors",
                        !day && "bg-white/10",
                        day && dayEntries.length > 0 && "cursor-pointer",
                        day && dayEntries.length === 0 && "cursor-default",
                        isSelected && "bg-indigo-50/70",
                        day && dayEntries.length > 0 && !isSelected && "hover:bg-white/50",
                      )}
                    >
                      {day && (
                        <>
                          <span
                            className={cn(
                              "inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-medium",
                              isToday(day)
                                ? "bg-indigo-600 text-white font-bold shadow-md shadow-indigo-200"
                                : "text-gray-500",
                            )}
                          >
                            {day}
                          </span>
                          <div className="mt-1 space-y-0.5">
                            {dayEntries.slice(0, 2).map((entry) => (
                              <div
                                key={entry.id}
                                className="rounded-md bg-indigo-500/10 px-1.5 py-0.5 text-xs font-medium text-indigo-700 truncate"
                                title={entry.restaurant_name}
                              >
                                {entry.restaurant_name}
                              </div>
                            ))}
                            {dayEntries.length > 2 && (
                              <div className="text-xs text-indigo-400 px-1">
                                +{dayEntries.length - 2} more
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Detail panel */}
          <div className="glass p-5 h-fit">
            {selectedDay && selectedEntries.length > 0 ? (
              <div>
                <div className="mb-4 flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold">
                      {tab === "team" ? "Team" : "My"} lunches
                    </p>
                    <p className="mt-0.5 text-base font-bold text-gray-900">{selectedDateLabel}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-600">
                    {selectedEntries.length} pick{selectedEntries.length > 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-3">
                  {selectedEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="rounded-xl border border-indigo-100/60 bg-white/60 p-3.5"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-100 to-violet-100 text-base">
                          <UtensilsCrossed className="h-4 w-4 text-indigo-500" />
                        </div>
                        <p className="flex-1 min-w-0 text-sm font-semibold text-gray-900 truncate">
                          {entry.restaurant_name || "Unknown"}
                        </p>
                      </div>
                      {entry.attendee_names.length > 0 && (
                        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-gray-400">
                          <Users className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">{entry.attendee_names.join(", ")}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : selectedDay ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
                  <UtensilsCrossed className="h-5 w-5 text-indigo-300" />
                </div>
                <p className="text-sm font-medium text-gray-500">{selectedDateLabel}</p>
                <p className="mt-1 text-xs text-gray-400">No lunches recorded</p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
                  <UtensilsCrossed className="h-5 w-5 text-indigo-300" />
                </div>
                <p className="text-sm text-gray-400">Click a day to see details</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
