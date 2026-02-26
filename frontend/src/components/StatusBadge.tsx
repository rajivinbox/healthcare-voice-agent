import React from "react";

export type AgentStatus =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "error";

const STATUS_CONFIG: Record<AgentStatus, { label: string; color: string; pulse: boolean }> = {
  idle:         { label: "Ready",        color: "#22c55e", pulse: false },
  recording:    { label: "Listening...", color: "#ef4444", pulse: true  },
  transcribing: { label: "Transcribing", color: "#f59e0b", pulse: true  },
  thinking:     { label: "Processing",   color: "#3b82f6", pulse: true  },
  speaking:     { label: "Speaking",     color: "#8b5cf6", pulse: true  },
  error:        { label: "Error",        color: "#ef4444", pulse: false },
};

interface Props {
  status: AgentStatus;
}

export default function StatusBadge({ status }: Props) {
  const { label, color, pulse } = STATUS_CONFIG[status];

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
          animation: pulse ? "pulse 1.2s ease-in-out infinite" : "none",
        }}
      />
      <span style={{ color: "#94a3b8", fontSize: 13, fontWeight: 500 }}>{label}</span>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}
