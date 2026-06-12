import { ChatDetail } from "./types";

const API_BASE = "http://localhost:7396";

export async function getChats(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/chats`);
  if (!res.ok) throw new Error("Failed to fetch chats");
  const data = await res.json();
  return data.chats;
}

export async function getChatDetail(name: string): Promise<ChatDetail> {
  const res = await fetch(`${API_BASE}/api/chat/${name}`);
  if (!res.ok) throw new Error("Failed to fetch chat detail");
  return res.json();
}

export function getArtifactUrl(uuid: string, path: string): string {
  return `${API_BASE}/api/brain/${uuid}/${path}`;
}
