// src/services/DataPreprocessingService.js
import apiAdmin from "./apiAdmin";
import { getSseToken } from "./SseTokenService";

const API_BASE_EXCELS = "/preprocessingexcels";
const API_BASE_REPORTS = "/preprocessingreports";

export const startPreprocessingExcels = async () => {
  const sseToken = await getSseToken();

  const url =
    `${apiAdmin.defaults.baseURL}${API_BASE_EXCELS}` +
    `?sse_token=${encodeURIComponent(sseToken)}`;

  const eventSource = new EventSource(url);

  eventSource.onopen = () => {
    console.log("🚀 SSE Excel sécurisé connecté");
  };

  eventSource.onerror = (err) => {
    console.error("❌ Erreur SSE Excel :", err);
    eventSource.close();
  };

  return eventSource;
};

export const startPreprocessingReports = async () => {
  const sseToken = await getSseToken();

  const url =
    `${apiAdmin.defaults.baseURL}${API_BASE_REPORTS}` +
    `?sse_token=${encodeURIComponent(sseToken)}`;

  const eventSource = new EventSource(url);

  eventSource.onopen = () => {
    console.log("🚀 SSE Reports sécurisé connecté");
  };

  eventSource.onerror = (err) => {
    console.error("❌ Erreur SSE Reports :", err);
    eventSource.close();
  };

  return eventSource;
};
