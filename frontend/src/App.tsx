import React, { useCallback, useEffect, useRef, useState } from "react";
import { Trash2, Activity } from "lucide-react";
import VoiceButton from "./components/VoiceButton";
import StatusBadge, { AgentStatus } from "./components/StatusBadge";
import ConversationLog from "./components/ConversationLog";
import {
  ConversationTurn,
  clearSession,
  getHealth,
  processAudio,
} from "./services/agentApi";

// Generate a stable session ID for the browser session
function makeSessionId() {
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [sessionId] = useState(makeSessionId);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Check backend health on mount
  useEffect(() => {
    getHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  const playAudio = useCallback((blob: Blob): Promise<void> => {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.play().catch(resolve);
    });
  }, []);

  const handleAudioReady = useCallback(
    async (audioBlob: Blob) => {
      setStatus("transcribing");

      try {
        setStatus("thinking");
        const result = await processAudio(audioBlob, sessionId);

        // Add user turn
        if (result.userText) {
          setTurns((prev) => [
            ...prev,
            { role: "user", text: result.userText, timestamp: Date.now() },
          ]);
        }

        // Add assistant turn
        if (result.responseText) {
          setTurns((prev) => [
            ...prev,
            { role: "assistant", text: result.responseText, timestamp: Date.now() },
          ]);
        }

        // Play response audio
        setStatus("speaking");
        await playAudio(result.audioBlob);
        setStatus("idle");
      } catch (err) {
        console.error("Pipeline error:", err);
        setStatus("error");
        setTurns((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "Sorry, I encountered an error. Please check the backend and try again.",
            timestamp: Date.now(),
          },
        ]);
        setTimeout(() => setStatus("idle"), 3000);
      }
    },
    [sessionId, playAudio]
  );

  const handleClear = useCallback(async () => {
    audioRef.current?.pause();
    setTurns([]);
    setStatus("idle");
    await clearSession(sessionId).catch(() => {});
  }, [sessionId]);

  const isProcessing = ["transcribing", "thinking", "speaking"].includes(status);

  return (
    <div style={styles.root}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <Activity size={20} color="#3b82f6" />
          <span style={styles.title}>Healthcare Voice Agent</span>
          <span style={styles.badge}>POC</span>
        </div>
        <div style={styles.headerRight}>
          {backendOnline !== null && (
            <span
              style={{
                ...styles.healthDot,
                background: backendOnline ? "#22c55e" : "#ef4444",
              }}
              title={backendOnline ? "Backend online" : "Backend offline"}
            />
          )}
          <StatusBadge status={status} />
          <button
            onClick={handleClear}
            title="Clear conversation"
            style={styles.clearBtn}
            disabled={turns.length === 0}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </header>

      {/* Conversation area */}
      <main style={styles.main}>
        <ConversationLog turns={turns} />
      </main>

      {/* Voice input footer */}
      <footer style={styles.footer}>
        {backendOnline === false && (
          <p style={styles.offlineWarning}>
            Backend is offline. Start the FastAPI server at localhost:8000.
          </p>
        )}
        <VoiceButton
          onAudioReady={handleAudioReady}
          disabled={isProcessing || backendOnline === false}
          status={status}
        />
      </footer>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    background: "#0f172a",
    color: "#f1f5f9",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 24px",
    borderBottom: "1px solid #1e293b",
    background: "#0f172a",
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  title: {
    fontWeight: 600,
    fontSize: 16,
    color: "#f1f5f9",
  },
  badge: {
    fontSize: 10,
    fontWeight: 700,
    background: "#1e3a5f",
    color: "#60a5fa",
    padding: "2px 6px",
    borderRadius: 4,
    letterSpacing: 0.5,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  healthDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    display: "inline-block",
  },
  clearBtn: {
    background: "none",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#64748b",
    cursor: "pointer",
    padding: "4px 8px",
    display: "flex",
    alignItems: "center",
  },
  main: {
    flex: 1,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    maxWidth: 760,
    width: "100%",
    margin: "0 auto",
    padding: "0 16px",
  },
  footer: {
    borderTop: "1px solid #1e293b",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "8px 0 16px",
    background: "#0f172a",
  },
  offlineWarning: {
    color: "#ef4444",
    fontSize: 12,
    marginBottom: 4,
  },
};
