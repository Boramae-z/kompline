
"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, PlusCircle, Scale, FileText } from "lucide-react"

const items = [
    {
        title: "Dashboard",
        href: "/",
        icon: LayoutDashboard,
    },
    {
        title: "Regulations",
        href: "/regulations",
        icon: FileText,
    },
]

interface MainNavProps extends React.HTMLAttributes<HTMLElement> { }

export function MainNav({ className, ...props }: MainNavProps) {
    const pathname = usePathname()

    return (
        <nav
            className={cn("flex space-x-2 lg:flex-col lg:space-x-0 lg:space-y-1", className)}
            {...props}
        >
            {items.map((item) => (
                <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                        "justify-start text-sm font-medium transition-colors hover:text-primary p-2 rounded-md flex items-center gap-2",
                        pathname === item.href
                            ? "bg-muted text-primary"
                            : "text-muted-foreground hover:bg-muted"
                    )}
                >
                    <item.icon className="h-4 w-4" />
                    {item.title}
                </Link>
            ))}
        </nav>
    )
}
