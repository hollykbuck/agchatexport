"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getChatDetail, getArtifactUrl } from "@/lib/api";
import { ChatDetail, Message } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  ArrowLeft, 
  FileText, 
  Cpu, 
  User, 
  Bot, 
  Terminal,
  ExternalLink 
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function ChatPage() {
  const { name } = useParams();
  const router = useRouter();
  const [data, setData] = useState<ChatDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (name) {
      getChatDetail(name as string)
        .then(setData)
        .finally(() => setLoading(false));
    }
  }, [name]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!data) return <div>Not found</div>;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <button 
            onClick={() => router.push("/")}
            className="flex items-center text-sm text-gray-500 hover:text-blue-600 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to list
          </button>
          <h1 className="text-xl font-bold text-gray-900 truncate" title={data.db_name}>
            {data.db_name}
          </h1>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center">
            <FileText className="w-4 h-4 mr-2" />
            Artifacts (Brain)
          </h3>
          <div className="space-y-2">
            {data.artifacts.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No artifacts found</p>
            ) : (
              data.artifacts.map((art) => (
                <a
                  key={art}
                  href={getArtifactUrl(data.db_uuid, art)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center p-2 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-700 rounded-lg transition-colors group"
                >
                  <span className="truncate flex-1">{art}</span>
                  <ExternalLink className="w-3 h-3 ml-2 opacity-0 group-hover:opacity-100" />
                </a>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto py-12 px-8">
          <div className="space-y-8">
            {data.messages.map((msg) => (
              <MessageBubble key={msg.idx} msg={msg} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "USER";
  const isAssistant = msg.role === "ASSISTANT";
  const isObservation = msg.role === "OBSERVATION";

  return (
    <div className={cn(
      "p-6 rounded-2xl shadow-sm border",
      isUser && "bg-blue-50 border-blue-100 ml-12",
      isAssistant && "bg-white border-gray-100 mr-12",
      isObservation && "bg-gray-100 border-gray-200 font-mono text-sm mx-6"
    )}>
      <div className="flex items-center gap-2 mb-3 text-xs font-bold uppercase tracking-wider text-gray-400">
        {isUser && <User className="w-4 h-4 text-blue-500" />}
        {isAssistant && <Bot className="w-4 h-4 text-green-500" />}
        {isObservation && <Terminal className="w-4 h-4 text-orange-500" />}
        <span>{msg.role} (Step {msg.idx})</span>
      </div>

      <div className="prose prose-sm max-w-none prose-pre:bg-gray-900 prose-pre:text-gray-100">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {msg.content}
        </ReactMarkdown>
      </div>

      {msg.tool_call && (
        <div className="mt-4 p-4 bg-gray-900 rounded-lg text-xs">
          <div className="flex items-center gap-2 text-blue-400 mb-2 font-mono">
            <Cpu className="w-4 h-4" />
            <span>PLANNING ACTION: {msg.tool_call.tool_name}</span>
          </div>
          <pre className="text-gray-300 overflow-x-auto">
            {JSON.stringify(msg.tool_call.args || msg.tool_call.args_raw, null, 2)}
          </pre>
        </div>
      )}

      {isObservation && msg.key && (
        <div className="mt-2 text-[10px] text-gray-400 font-mono">
          KEY: {msg.key}
        </div>
      )}
    </div>
  );
}
