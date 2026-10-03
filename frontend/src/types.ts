export type Route = "retrieve" | "web_search" | "clarify";

export interface Source {
  id: number;
  kind: "document" | "web";
  source: string;
  page: number | null;
  url: string | null;
  snippet: string;
  score: number | null;
}

export interface DocumentInfo {
  filename: string;
  pages: number;
  chunks: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: Route;
  routeReason?: string;
  fellBack?: boolean;
  sources?: Source[];
  pending?: boolean;
  error?: boolean;
  stopped?: boolean;
}
