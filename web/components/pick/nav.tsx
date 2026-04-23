"use client";

import { useQuery } from "@tanstack/react-query";
import { LogOut, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout } from "@/lib/auth";
import { cn } from "@/lib/utils";

const links = [
  { href: "/blacklist", label: "Blacklist" },
  { href: "/history", label: "History" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getMe });

  if (!user) return null;

  const initials = user.name
    ? user.name
        .split(" ")
        .map((p: string) => p[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <header className="glass-nav sticky top-0 z-10">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-center gap-2">
            <UtensilsCrossed className="h-5 w-5 text-indigo-600" />
            <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              PICK
            </span>
          </Link>
          <nav className="flex gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                  pathname === link.href
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:bg-indigo-50 hover:text-indigo-600"
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-md shadow-indigo-200">
            {initials}
          </div>
          <span className="text-sm text-gray-500">{user.name}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-full border border-white/80 bg-white/70 px-3 py-1.5 text-xs text-gray-500 transition-colors hover:bg-white hover:text-gray-700"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
