import React, { useEffect, useRef } from "react";
import { ConversationTurn } from "../services/agentApi";

interface Props {
  turns: ConversationTurn[];
}

export default function ConversationLog({ turns }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  if (turns.length === 0) {
    return (
      <div style={styles.emptyState}>
        <p style={styles.emptyText}>Hold the button and speak to start a conversation</p>
        <p style={styles.exampleHint}>
          Try: "Book an appointment for Alice Johnson with Dr. Smith tomorrow at 2 PM for a checkup"
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {turns.map((turn, i) => (
        <div
          key={i}
          style={{
            ...styles.bubble,
            ...(turn.role === "user" ? styles.userBubble : styles.agentBubble),
          }}
        >
          <div style={styles.roleLabel}>
            {turn.role === "user" ? "You" : "Agent"}
          </div>
          <div style={styles.text}>{turn.text}</div>
          <div style={styles.timestamp}>
            {new Date(turn.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    padding: "16px 8px",
    overflowY: "auto",
    flex: 1,
  },
  emptyState: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 32,
  },
  emptyText: {
    color: "#64748b",
    fontSize: 16,
    textAlign: "center",
  },
  exampleHint: {
    color: "#475569",
    fontSize: 13,
    fontStyle: "italic",
    textAlign: "center",
    maxWidth: 480,
  },
  bubble: {
    maxWidth: "75%",
    borderRadius: 12,
    padding: "10px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  userBubble: {
    alignSelf: "flex-end",
    background: "#1e40af",
    borderBottomRightRadius: 2,
  },
  agentBubble: {
    alignSelf: "flex-start",
    background: "#1e293b",
    border: "1px solid #334155",
    borderBottomLeftRadius: 2,
  },
  roleLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: "#94a3b8",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  text: {
    color: "#f1f5f9",
    fontSize: 14,
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
  },
  timestamp: {
    fontSize: 10,
    color: "#64748b",
    alignSelf: "flex-end",
  },
};
