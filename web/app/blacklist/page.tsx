"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Check, Loader2, Search, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { getMe } from "@/lib/auth";
import { useDebouncedValue } from "@/lib/hooks";
import { Nav } from "@/components/pick/nav";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Restaurant {
  id: string;
  name: string;
  rating: number | null;
  source: string;
  vicinity: string | null;
}

interface BlacklistEntry {
  id: string;
  user_id: string;
  restaurant_id: string;
  restaurant_name: string;
  mode: string;
  expires_at: string | null;
  created_at: string;
}

export default function BlacklistPage() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkAdding, setBulkAdding] = useState(false);
  const [selectedToRemove, setSelectedToRemove] = useState<Set<string>>(new Set());
  const [bulkRemoving, setBulkRemoving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getMe });

  const { data: allRestaurants, isLoading: loadingRestaurants } = useQuery({
    queryKey: ["restaurants-all"],
    queryFn: async () => {
      const res = await api.get("/restaurants?page_size=100");
      return res.json();
    },
  });

  const { data: blacklist, isLoading: loadingBlacklist } = useQuery({
    queryKey: ["blacklist"],
    queryFn: () =>
      api.get(`/blacklist?user_id=${user!.user_id}`).then((r) => r.json()),
    enabled: !!user,
  });

  const entries: BlacklistEntry[] = blacklist?.entries || [];
  const blacklistedIds = useMemo(
    () => new Set(entries.map((e) => e.restaurant_id)),
    [entries],
  );
  const permanent = entries.filter((e) => e.mode === "permanent");
  const today = entries.filter((e) => e.mode === "today");

  const restaurants: Restaurant[] = allRestaurants?.restaurants || [];
  const filtered = useMemo(() => {
    const q = debouncedQuery.toLowerCase();
    return restaurants.filter(
      (r) => !blacklistedIds.has(r.id) && (!q || r.name.toLowerCase().includes(q)),
    );
  }, [restaurants, blacklistedIds, debouncedQuery]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((r) => r.id)));
    }
  }

  async function bulkAdd(mode: "permanent" | "today") {
    if (!user || selected.size === 0) return;
    setBulkAdding(true);
    try {
      await Promise.all(
        Array.from(selected).map((restaurant_id) =>
          api.post(`/blacklist?user_id=${user.user_id}`, { restaurant_id, mode }),
        ),
      );
      queryClient.invalidateQueries({ queryKey: ["blacklist"] });
      toast.success(`Added ${selected.size} restaurant${selected.size > 1 ? "s" : ""} to blacklist`);
      setSelected(new Set());
    } catch {
      toast.error("Failed to add some restaurants");
    } finally {
      setBulkAdding(false);
    }
  }

  function toggleRemove(id: string) {
    setSelectedToRemove((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAllInSection(sectionEntries: BlacklistEntry[]) {
    const ids = sectionEntries.map((e) => e.id);
    const allSelected = ids.every((id) => selectedToRemove.has(id));
    setSelectedToRemove((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        ids.forEach((id) => next.delete(id));
      } else {
        ids.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  async function bulkRemove() {
    if (!user || selectedToRemove.size === 0) return;
    setBulkRemoving(true);
    try {
      await Promise.all(
        Array.from(selectedToRemove).map((id) =>
          api.delete(`/blacklist/${id}?user_id=${user.user_id}`),
        ),
      );
      queryClient.invalidateQueries({ queryKey: ["blacklist"] });
      toast.success(`Removed ${selectedToRemove.size} restaurant${selectedToRemove.size > 1 ? "s" : ""} from blacklist`);
      setSelectedToRemove(new Set());
      setConfirmRemove(false);
    } catch {
      toast.error("Failed to remove some restaurants");
    } finally {
      setBulkRemoving(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10 space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
            My{" "}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              Blacklist
            </span>
          </h1>
          <p className="mt-1 text-sm text-gray-400">
            Restaurants you don&apos;t want to see in recommendations
          </p>
        </div>

        {/* Search + toolbar */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Filter restaurants..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-full border border-white/80 bg-white/70 py-2.5 pl-10 pr-10 text-sm backdrop-blur-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          {filtered.length > 0 && (
            <button
              onClick={selectAll}
              className="text-sm text-indigo-600 hover:underline whitespace-nowrap"
            >
              {selected.size === filtered.length ? "Deselect all" : "Select all"}
            </button>
          )}
        </div>

        {/* Restaurant list card */}
        <div className="glass overflow-hidden">
          <div className="flex items-center justify-between px-6 py-3 border-b border-white/60 bg-white/30">
            <span className="text-sm font-medium text-gray-500">
              Available ({filtered.length})
            </span>
            {selected.size > 0 && (
              <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-600">
                {selected.size} selected
              </span>
            )}
          </div>

          {loadingRestaurants ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="px-6 py-8 text-sm text-gray-400 text-center">
              {query ? "No matching restaurants" : "All restaurants are blacklisted"}
            </p>
          ) : (
            <div className="max-h-[50vh] overflow-y-auto divide-y divide-white/50">
              {filtered.map((r) => (
                <label
                  key={r.id}
                  className={`flex items-center gap-4 px-6 py-3.5 cursor-pointer transition-colors ${
                    selected.has(r.id) ? "bg-indigo-50/60" : "hover:bg-white/40"
                  }`}
                  onClick={() => toggleSelect(r.id)}
                >
                  <GlassCheckbox checked={selected.has(r.id)} />
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-100 to-violet-100 text-lg">
                    🍽️
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-gray-900 truncate">{r.name}</p>
                    <p className="text-xs text-gray-400">
                      {r.rating ? `${r.rating} ★ · ` : ""}
                      {r.source === "google_maps" ? "Google Maps" : "Manual"}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Bulk add action bar */}
        {selected.size > 0 && (
          <div className="flex gap-3 sticky bottom-6">
            <button
              className="flex flex-1 items-center justify-center gap-2 rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-60"
              onClick={() => bulkAdd("permanent")}
              disabled={bulkAdding}
            >
              {bulkAdding ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Ban className="h-4 w-4" />
              )}
              Ban permanently ({selected.size})
            </button>
            <button
              className="flex flex-1 items-center justify-center gap-2 rounded-full border border-white/80 bg-white/80 px-5 py-3 text-sm font-semibold text-gray-700 backdrop-blur-sm shadow-sm transition hover:bg-white disabled:opacity-60"
              onClick={() => bulkAdd("today")}
              disabled={bulkAdding}
            >
              {bulkAdding ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Ban className="h-4 w-4 text-indigo-500" />
              )}
              Skip today ({selected.size})
            </button>
          </div>
        )}

        {/* Current blacklist entries */}
        {loadingBlacklist ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
          </div>
        ) : (
          entries.length > 0 && (
            <div className="space-y-4">
              {permanent.length > 0 && (
                <BlacklistSection
                  title="Permanent"
                  entries={permanent}
                  selectedToRemove={selectedToRemove}
                  onToggle={toggleRemove}
                  onSelectAll={() => selectAllInSection(permanent)}
                />
              )}
              {today.length > 0 && (
                <BlacklistSection
                  title="Today only"
                  entries={today}
                  selectedToRemove={selectedToRemove}
                  onToggle={toggleRemove}
                  onSelectAll={() => selectAllInSection(today)}
                />
              )}
            </div>
          )
        )}

        {/* Bulk remove button */}
        {selectedToRemove.size > 0 && (
          <div className="sticky bottom-6">
            <button
              className="flex w-full items-center justify-center gap-2 rounded-full bg-red-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-red-100 transition hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-60"
              onClick={() => setConfirmRemove(true)}
            >
              <Trash2 className="h-4 w-4" />
              Remove from blacklist ({selectedToRemove.size})
            </button>
          </div>
        )}

        {/* Confirm dialog */}
        <Dialog open={confirmRemove} onOpenChange={setConfirmRemove}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Remove {selectedToRemove.size} restaurant{selectedToRemove.size > 1 ? "s" : ""} from blacklist?
              </DialogTitle>
              <DialogDescription>
                These restaurants will appear in recommendations again.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <button
                className="rounded-full border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                onClick={() => setConfirmRemove(false)}
              >
                Cancel
              </button>
              <button
                className="flex items-center gap-2 rounded-full bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-60"
                onClick={bulkRemove}
                disabled={bulkRemoving}
              >
                {bulkRemoving && <Loader2 className="h-4 w-4 animate-spin" />}
                Remove
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </>
  );
}

function GlassCheckbox({ checked }: { checked: boolean }) {
  return (
    <div
      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all ${
        checked
          ? "border-indigo-600 bg-gradient-to-br from-indigo-600 to-violet-600 text-white"
          : "border-gray-300 bg-white/80"
      }`}
    >
      {checked && <Check className="h-3 w-3" />}
    </div>
  );
}

function BlacklistSection({
  title,
  entries,
  selectedToRemove,
  onToggle,
  onSelectAll,
}: {
  title: string;
  entries: BlacklistEntry[];
  selectedToRemove: Set<string>;
  onToggle: (id: string) => void;
  onSelectAll: () => void;
}) {
  const allSelected = entries.every((e) => selectedToRemove.has(e.id));

  return (
    <div className="glass overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/60 bg-white/30">
        <span className="text-sm font-medium text-gray-500">
          {title} ({entries.length})
        </span>
        <button
          onClick={onSelectAll}
          className="text-xs text-indigo-600 hover:underline"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>
      <div className="divide-y divide-white/50">
        {entries.map((entry) => (
          <label
            key={entry.id}
            className={`flex items-center gap-4 px-6 py-3.5 cursor-pointer transition-colors ${
              selectedToRemove.has(entry.id) ? "bg-red-50/50" : "hover:bg-white/40"
            }`}
            onClick={() => onToggle(entry.id)}
          >
            <GlassCheckbox checked={selectedToRemove.has(entry.id)} />
            <Ban className="h-4 w-4 text-red-400 shrink-0" />
            <span className="flex-1 min-w-0 truncate text-sm font-medium text-gray-800">
              {entry.restaurant_name || entry.restaurant_id}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
