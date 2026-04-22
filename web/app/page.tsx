"use client";

import { UtensilsCrossed } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { buttonVariants } from "@/components/ui/button";

function LandingContent() {
  const params = useSearchParams();
  const expired = params.get("expired");

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="text-center space-y-6 max-w-md">
        <UtensilsCrossed className="h-16 w-16 mx-auto text-primary" />
        <h1 className="text-4xl font-bold">PICK</h1>
        <p className="text-lg text-muted-foreground">
          Lunch Bot — pair from Telegram to manage your preferences
        </p>
        {expired && (
          <p className="text-sm text-destructive">
            Session expired. Please pair again from Telegram.
          </p>
        )}
        <a
          href="https://t.me/pick_food_bot"
          target="_blank"
          className={buttonVariants({ size: "lg" })}
        >
          Open Telegram Bot
        </a>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <LandingContent />
    </Suspense>
  );
}
