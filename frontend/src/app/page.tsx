"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getChats } from "@/lib/api";
import { MessageSquare, Database } from "lucide-react";

export default function Home() {
  const [chats, setChats] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getChats()
      .then(setChats)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <header className="mb-12 flex items-center gap-3">
        <Database className="w-8 h-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Conversations</h1>
      </header>

      <div className="grid gap-4">
        {chats.length === 0 ? (
          <p className="text-gray-500 italic text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
            No conversations found.
          </p>
        ) : (
          chats.map((name) => (
            <Link
              key={name}
              href={`/chat?name=${name}`}
              className="group flex items-center p-4 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md hover:border-blue-300 transition-all"
            >
              <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div className="ml-4 flex-1">
                <h2 className="font-semibold text-gray-800">{name}</h2>
                <p className="text-sm text-gray-500">SQLite Database</p>
              </div>
              <div className="text-blue-500 font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity">
                Open Chat →
              </div>
            </Link>
          ))
        )}
      </div>
    </main>
  );
}
