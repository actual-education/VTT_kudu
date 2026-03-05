"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const imported = await api.importVideo(url.trim());
      setUrl("");
      router.push(`/videos?imported=${imported.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            AVCE
          </h1>
          <p className="text-lg text-gray-600">
            ADA Visual Compliance Engine
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Analyze YouTube educational videos for ADA/WCAG 2.1 AA compliance
          </p>
        </div>

        <form onSubmit={handleImport} className="max-w-2xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste YouTube URL (e.g., https://youtube.com/watch?v=...)"
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-gray-900"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {loading ? "Importing..." : "Import"}
            </button>
          </div>
          {error && (
            <p className="mt-3 text-red-600 text-sm">{error}</p>
          )}
        </form>

        <div className="mt-8 text-center">
          <Link
            href="/videos"
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            View all videos →
          </Link>
        </div>
      </div>
    </main>
  );
}
