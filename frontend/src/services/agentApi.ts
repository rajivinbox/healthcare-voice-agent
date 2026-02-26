import axios from "axios";

const BASE = "/api";

export interface ConversationTurn {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

export interface AudioResponse {
  audioBlob: Blob;
  userText: string;
  responseText: string;
  sessionId: string;
  goalAchieved: boolean;
}

export interface TextResponse {
  session_id: string;
  user_text: string;
  response_text: string;
  goal_achieved: boolean;
}

/**
 * Send audio blob to the backend.
 * Returns the TTS audio plus metadata from response headers.
 */
export async function processAudio(
  audioBlob: Blob,
  sessionId: string
): Promise<AudioResponse> {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("session_id", sessionId);

  const response = await axios.post(`${BASE}/process-audio`, form, {
    responseType: "arraybuffer",
    headers: { "Content-Type": "multipart/form-data" },
  });

  const audioResponse = new Blob([response.data], { type: "audio/mpeg" });
  const headers = response.headers;

  return {
    audioBlob: audioResponse,
    userText: decodeURIComponent(headers["x-user-text"] ?? ""),
    responseText: decodeURIComponent(headers["x-response-text"] ?? ""),
    sessionId: headers["x-session-id"] ?? sessionId,
    goalAchieved: headers["x-goal-achieved"] === "true",
  };
}

/** Send text (bypass STT/TTS — for testing) */
export async function processText(
  text: string,
  sessionId: string
): Promise<TextResponse> {
  const { data } = await axios.post<TextResponse>(`${BASE}/process-text`, {
    text,
    session_id: sessionId,
  });
  return data;
}

/** Health check */
export async function getHealth() {
  const { data } = await axios.get(`${BASE}/health`);
  return data;
}

/** Clear session history */
export async function clearSession(sessionId: string) {
  await axios.delete(`${BASE}/session/${sessionId}`);
}
