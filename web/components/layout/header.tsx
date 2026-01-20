"use client";

import { useEffect, useState } from "react";
import { Bell, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { healthCheck } from "@/lib/api";

interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    const checkApi = async () => {
      const isOnline = await healthCheck();
      setApiStatus(isOnline ? "online" : "offline");
    };
    checkApi();
    const interval = setInterval(checkApi, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-6">
        <div>
          <h1 className="text-xl font-semibold">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* API Status */}
          <div className="flex items-center gap-2">
            <Circle
              className={cn(
                "h-2 w-2 fill-current",
                apiStatus === "online" && "text-green-500",
                apiStatus === "offline" && "text-red-500",
                apiStatus === "checking" && "text-yellow-500"
              )}
            />
            <span className="text-xs text-muted-foreground">
              {apiStatus === "online" && "API Connected"}
              {apiStatus === "offline" && "API Offline"}
              {apiStatus === "checking" && "Checking..."}
            </span>
          </div>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            <Badge
              variant="error"
              className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-[10px]"
            >
              3
            </Badge>
          </Button>
        </div>
      </div>
    </header>
  );
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
