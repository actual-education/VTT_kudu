"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

export function Header() {
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    } finally {
      router.push("/login");
      router.refresh();
    }
  };

  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center px-4 shrink-0">
      <Link href="/" className="font-bold text-lg text-gray-900 mr-8">
        AVCE
      </Link>
      <nav className="flex gap-6 text-sm">
        <Link href="/" className="text-gray-600 hover:text-gray-900">
          Dashboard
        </Link>
        <Link href="/videos" className="text-gray-600 hover:text-gray-900">
          Videos
        </Link>
      </nav>
      <button
        onClick={handleLogout}
        className="ml-auto text-xs px-2.5 py-1.5 rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
      >
        Logout
      </button>
    </header>
  );
}
