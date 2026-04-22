"use client";

import { useQuery } from "@tanstack/react-query";
import { LogOut, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout } from "@/lib/auth";
import { Button } from "@/components/ui/button";
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

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <UtensilsCrossed className="h-5 w-5" />
            PICK
          </Link>
          <nav className="flex gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  pathname === link.href
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{user.name}</span>
          <Button variant="ghost" size="icon" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
