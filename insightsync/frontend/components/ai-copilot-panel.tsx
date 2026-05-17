"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  Send,
  Sparkles,
  Globe,
  TrendingUp,
  FileText,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { postJson } from "@/lib/api-client";

interface AICopilotPanelProps {
  isOpen: boolean;
  onClose: () => void;
  prospectId?: string;
  autoPrompt?: string | null;
}

const samplePrompts = [
  {
    icon: Sparkles,
    prompt: "Why is this company high priority?",
    label: "Priority explanation",
  },
  {
    icon: TrendingUp,
    prompt: "What changed recently?",
    label: "Recent changes",
  },
  {
    icon: MessageSquare,
    prompt: "What should I say in the first meeting?",
    label: "Meeting prep",
  },
  {
    icon: FileText,
    prompt: "What products should I pitch first?",
    label: "Product recommendations",
  },
  {
    icon: Globe,
    prompt: "Summarize the most relevant signals",
    label: "Signal summary",
  },
];

export function AICopilotPanel({
  isOpen,
  onClose,
  prospectId,
  autoPrompt,
}: AICopilotPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const lastAutoPromptRef = useRef<string | null>(null);

  const handleSubmit = useCallback(async (prompt: string) => {
    if (!prompt.trim()) return;

    const userMessage = prompt.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setIsLoading(true);

    try {
      const data = prospectId
        ? await postJson<
            { answer?: string; status?: string },
            { question: string; include_chunks: boolean }
          >(`/api/prospects/${encodeURIComponent(prospectId)}/question`, {
            question: userMessage,
            include_chunks: false,
          })
        : await postJson<
            { answer?: string; status?: string },
            { question: string; include_chunks: boolean }
          >("/api/rag/query", {
            question: userMessage,
            include_chunks: false,
          });

      const result = data as {
        answer?: string;
        status?: string;
      };

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            result.answer ||
            "I could not find enough evidence to answer that. Try asking about priority, signals, meeting prep, or product recommendations.",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I could not reach the copilot service. Please check that the InsightSync backend is running, then try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [prospectId]);

  const handlePromptClick = (prompt: string) => {
    handleSubmit(prompt);
  };

  useEffect(() => {
    if (!isOpen || !autoPrompt || lastAutoPromptRef.current === autoPrompt) return;
    lastAutoPromptRef.current = autoPrompt;
    handleSubmit(autoPrompt);
  }, [autoPrompt, handleSubmit, isOpen]);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-[480px] transform border-l border-border bg-card shadow-2xl transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                AI Copilot
              </h2>
              <p className="text-xs text-muted-foreground">
                Intelligence assistant
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Messages Area */}
        <div className="flex h-[calc(100%-140px)] flex-col overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-full bg-primary/10 p-4">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h3 className="mb-2 text-base font-semibold text-foreground">
                Ask AI Copilot
              </h3>
              <p className="mb-6 max-w-sm text-sm text-muted-foreground">
                Get insights based on the signals and prospects shown on your
                dashboard
              </p>

              {/* Sample Prompts */}
              <div className="w-full space-y-2">
                {samplePrompts.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handlePromptClick(item.prompt)}
                    className="flex w-full items-center gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/50"
                  >
                    <div className="rounded-md bg-primary/10 p-1.5">
                      <item.icon className="h-4 w-4 text-primary" />
                    </div>
                    <span className="text-sm text-foreground">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "rounded-lg p-3",
                    message.role === "user"
                      ? "ml-8 bg-primary text-primary-foreground"
                      : "mr-4 border border-border bg-muted/30"
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="mb-2 flex items-center gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs font-medium text-primary">
                        AI Copilot
                      </span>
                      <Badge variant="outline" className="text-[9px]">
                        Evidence-grounded
                      </Badge>
                    </div>
                  )}
                  <div
                    className={cn(
                      "whitespace-pre-wrap text-sm",
                      message.role === "assistant" && "prose prose-sm max-w-none text-foreground prose-headings:text-foreground prose-strong:text-foreground prose-p:text-foreground"
                    )}
                    dangerouslySetInnerHTML={{
                      __html: message.content
                        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                        .replace(/\n/g, "<br />"),
                    }}
                  />
                </div>
              ))}
              {isLoading && (
                <div className="mr-4 flex items-center gap-2 rounded-lg border border-border bg-muted/30 p-3">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">
                    Analyzing dashboard data...
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-card p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about signals, prospects, or meeting prep..."
              className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <Button type="submit" size="icon" disabled={!input.trim() || isLoading}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
          <p className="mt-2 text-center text-[10px] text-muted-foreground">
            Responses based on visible dashboard data. Verify before use.
          </p>
        </div>
      </div>
    </>
  );
}

// Floating button component
export function AICopilotButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-all hover:scale-105 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
    >
      <Sparkles className="h-6 w-6" />
    </button>
  );
}
