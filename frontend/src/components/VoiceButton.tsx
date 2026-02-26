import React, { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Square } from "lucide-react";
import { AgentStatus } from "./StatusBadge";

interface Props {
  onAudioReady: (blob: Blob) => void;
  disabled: boolean;
  status: AgentStatus;
}

export default function VoiceButton({ onAudioReady, disabled, status }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    if (isRecording || disabled) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        onAudioReady(blob);
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      };

      recorder.start(250); // collect chunks every 250ms
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      alert("Microphone access is required. Please allow microphone access and try again.");
    }
  }, [isRecording, disabled, onAudioReady]);

  const stopRecording = useCallback(() => {
    if (!isRecording) return;
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }, [isRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const isActive = isRecording || status === "recording";
  const isProcessing = ["transcribing", "thinking", "speaking"].includes(status);

  return (
    <div style={styles.wrapper}>
      {/* Ripple rings when recording */}
      {isActive && (
        <>
          <span style={{ ...styles.ring, animationDelay: "0s" }} />
          <span style={{ ...styles.ring, animationDelay: "0.4s" }} />
          <span style={{ ...styles.ring, animationDelay: "0.8s" }} />
        </>
      )}

      <button
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
        onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
        disabled={disabled || isProcessing}
        style={{
          ...styles.button,
          ...(isActive ? styles.buttonActive : {}),
          ...(isProcessing ? styles.buttonDisabled : {}),
        }}
        aria-label={isRecording ? "Release to send" : "Hold to speak"}
      >
        {isActive ? (
          <Square size={28} color="#fff" fill="#fff" />
        ) : isProcessing ? (
          <Mic size={28} color="#64748b" />
        ) : (
          <Mic size={28} color="#fff" />
        )}
      </button>

      <p style={styles.hint}>
        {isActive
          ? "Release to send"
          : isProcessing
          ? "Processing..."
          : "Hold to speak"}
      </p>

      <style>{`
        @keyframes ripple {
          0% { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(2.2); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

const BUTTON_SIZE = 80;

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: "relative",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    padding: 24,
  },
  ring: {
    position: "absolute",
    top: "50%",
    left: "50%",
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    marginTop: -BUTTON_SIZE / 2 - 12, // account for gap above hint
    marginLeft: -BUTTON_SIZE / 2,
    borderRadius: "50%",
    border: "2px solid #ef4444",
    animation: "ripple 1.4s ease-out infinite",
    pointerEvents: "none",
  },
  button: {
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    borderRadius: "50%",
    border: "none",
    background: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 24px rgba(59, 130, 246, 0.4)",
    transition: "transform 0.1s, box-shadow 0.1s",
    outline: "none",
    zIndex: 1,
  },
  buttonActive: {
    background: "linear-gradient(135deg, #ef4444, #b91c1c)",
    boxShadow: "0 4px 24px rgba(239, 68, 68, 0.5)",
    transform: "scale(0.96)",
  },
  buttonDisabled: {
    background: "#1e293b",
    boxShadow: "none",
    cursor: "not-allowed",
  },
  hint: {
    fontSize: 12,
    color: "#64748b",
    userSelect: "none",
  },
};
