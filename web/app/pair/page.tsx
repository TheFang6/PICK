"use client";

import { Loader2, UtensilsCrossed, AlertCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function PairContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("No pairing token provided");
      return;
    }

    api.post("/pair", { token })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Pairing failed");
        }
        setStatus("success");
        setTimeout(() => router.push("/blacklist"), 1500);
      })
      .catch((err) => {
        setStatus("error");
        setError(err.message);
      });
  }, [token, router]);

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <UtensilsCrossed className="h-10 w-10 mx-auto text-primary" />
          <CardTitle>Pairing</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          {status === "loading" && (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Connecting your account...</p>
            </div>
          )}
          {status === "success" && (
            <div className="space-y-2">
              <p className="text-green-600 font-medium">Paired successfully!</p>
              <p className="text-sm text-muted-foreground">Redirecting...</p>
            </div>
          )}
          {status === "error" && (
            <div className="space-y-4">
              <div className="flex flex-col items-center gap-2 text-destructive">
                <AlertCircle className="h-8 w-8" />
                <p className="text-sm">{error}</p>
              </div>
              <a
                href="https://t.me/pick_food_bot"
                target="_blank"
                className={buttonVariants({ variant: "outline" })}
              >
                Back to Telegram
              </a>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

export default function PairPage() {
  return (
    <Suspense>
      <PairContent />
    </Suspense>
  );
}
