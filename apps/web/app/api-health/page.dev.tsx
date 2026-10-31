"use client";

import { useEffect, useState } from "react";

type ApiStatus = "checking" | "online" | "offline";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const controller = new AbortController();

    async function checkApi() {
      try {
        const response = await fetch(`${apiUrl}/api/v1/health`, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Health check returned ${response.status}`);
        }

        const body: unknown = await response.json();
        const isHealthy =
          typeof body === "object" &&
          body !== null &&
          "status" in body &&
          body.status === "ok";
        setApiStatus(isHealthy ? "online" : "offline");
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setApiStatus("offline");
        }
      }
    }

    void checkApi();
    return () => controller.abort();
  }, []);

  const label =
    apiStatus === "checking" ? "Checking…" : apiStatus === "online" ? "Online" : "Offline";

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <section className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-950 p-10 shadow-2xl">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.24em] text-red-400">
          Phase 1 Foundation
        </p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Red-Team Arena</h1>
        <p className="mt-4 text-lg text-zinc-400">AI Security Assessment Platform</p>

        <div className="mt-10 flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/60 px-5 py-4">
          <span className="font-medium text-zinc-300">API</span>
          <span
            aria-live="polite"
            className={`flex items-center gap-2 font-semibold ${
              apiStatus === "online"
                ? "text-emerald-400"
                : apiStatus === "offline"
                  ? "text-red-400"
                  : "text-amber-300"
            }`}
          >
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                apiStatus === "online"
                  ? "bg-emerald-400"
                  : apiStatus === "offline"
                    ? "bg-red-400"
                    : "animate-pulse bg-amber-300"
              }`}
            />
            {label}
          </span>
        </div>
      </section>
    </main>
  );
}

