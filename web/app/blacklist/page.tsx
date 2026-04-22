"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Check, Loader2, Search, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { getMe } from "@/lib/auth";
import { useDebouncedValue } from "@/lib/hooks";
import { Nav } from "@/components/pick/nav";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

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
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-6 space-y-6">
        <h1 className="text-2xl font-bold">Blacklist</h1>

        {/* Search filter */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Filter restaurants..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Restaurant list with checkboxes */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-muted-foreground">
              Restaurants ({filtered.length})
            </h2>
            {filtered.length > 0 && (
              <button
                onClick={selectAll}
                className="text-xs text-primary hover:underline"
              >
                {selected.size === filtered.length ? "Deselect all" : "Select all"}
              </button>
            )}
          </div>

          {loadingRestaurants ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              {query ? "No matching restaurants" : "All restaurants are blacklisted"}
            </p>
          ) : (
            <div className="space-y-1 max-h-[50vh] overflow-y-auto rounded-md border p-2">
              {filtered.map((r) => (
                <label
                  key={r.id}
                  className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => toggleSelect(r.id)}
                >
                  <Checkbox checked={selected.has(r.id)} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{r.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {r.rating ? `${r.rating} ★` : ""}{" "}
                      {r.source === "google_maps" ? "Maps" : "Manual"}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Bulk add buttons */}
        {selected.size > 0 && (
          <div className="flex gap-2 sticky bottom-4">
            <Button
              className="flex-1"
              onClick={() => bulkAdd("permanent")}
              disabled={bulkAdding}
            >
              {bulkAdding ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Ban className="h-4 w-4 mr-2" />
              )}
              Permanent ({selected.size})
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              onClick={() => bulkAdd("today")}
              disabled={bulkAdding}
            >
              {bulkAdding ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Ban className="h-4 w-4 mr-2" />
              )}
              Today only ({selected.size})
            </Button>
          </div>
        )}

        {/* Current blacklist entries */}
        {loadingBlacklist ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-4 space-y-1">
            <p className="text-muted-foreground text-sm">No blacklist entries yet</p>
          </div>
        ) : (
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
        )}

        {/* Bulk remove button */}
        {selectedToRemove.size > 0 && (
          <div className="sticky bottom-4">
            <Button
              variant="destructive"
              className="w-full"
              onClick={() => setConfirmRemove(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Remove ({selectedToRemove.size})
            </Button>
          </div>
        )}

        {/* Confirm bulk remove dialog */}
        <Dialog open={confirmRemove} onOpenChange={setConfirmRemove}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Remove {selectedToRemove.size} restaurant{selectedToRemove.size > 1 ? "s" : ""} from blacklist?</DialogTitle>
              <DialogDescription>
                These restaurants will appear in recommendations again.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmRemove(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={bulkRemove}
                disabled={bulkRemoving}
              >
                {bulkRemoving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Remove"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </>
  );
}

function Checkbox({ checked }: { checked: boolean }) {
  return (
    <div
      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${
        checked
          ? "bg-primary border-primary text-primary-foreground"
          : "border-muted-foreground/30"
      }`}
    >
      {checked && <Check className="h-3.5 w-3.5" />}
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
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-medium text-muted-foreground">{title} ({entries.length})</h2>
        <button
          onClick={onSelectAll}
          className="text-xs text-primary hover:underline"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>
      <div className="space-y-1 rounded-md border p-2">
        {entries.map((entry) => (
          <label
            key={entry.id}
            className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer hover:bg-accent transition-colors"
            onClick={() => onToggle(entry.id)}
          >
            <Checkbox checked={selectedToRemove.has(entry.id)} />
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <Ban className="h-4 w-4 text-destructive shrink-0" />
              <span className="font-medium text-sm truncate">
                {entry.restaurant_name || entry.restaurant_id}
              </span>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
