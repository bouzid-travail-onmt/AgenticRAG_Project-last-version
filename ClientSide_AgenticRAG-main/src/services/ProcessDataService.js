// src/services/ProcessDataService.js
import apiAdmin from "./apiAdmin";

export const uploadData = async (files, urls, headers = {}) => {
  const formData = new FormData();

  files.forEach((file) => formData.append("files", file));

  const urlsArray = urls
    .split(/[\n,]+/)          // 🔥 split par retour à la ligne OU virgule
    .filter((u) => u.length > 0); // 🔥 garder seulement les lignes non vides

  urlsArray.forEach((u) => formData.append("source_urls", u));

  const config = {
    headers: {
      ...headers,
      "Content-Type": "multipart/form-data",
    },
    responseType: "text", // ✅ pour recevoir le flux texte complet
  };

  return apiAdmin.post("/upload", formData, config);
};
