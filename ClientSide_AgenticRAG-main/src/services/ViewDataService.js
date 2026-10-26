// src/services/ViewDataService.js
import axios from "axios";
import apiAdmin from "./apiAdmin";
/* ================= BASE URLS ================= */
const API_BASE_FILES = "/files";
const API_BASE_FILES_RECENT = "/files/recent";
const API_BASE_INDICATORS_PRIVATE = "/indicators";
const API_BASE_INDICATORS_PUBLIC =
  "/api/public/indicators";
const API_BASE_ES = "/es";
/* ================= FILES (ADMIN) ================= */
export const fetchFiles = async (type) => {
  const res = await apiAdmin.get(
    `${API_BASE_FILES}?type=${encodeURIComponent(type)}`
  );
  return res.data || [];
};

export const fetchFilesRecent = async (type) => {
  const res = await apiAdmin.get(
    `${API_BASE_FILES_RECENT}?type=${encodeURIComponent(type)}`
  );
  return res.data || [];
};

/* ================= INDICATORS (ADMIN / PRIVATE) ================= */

export const fetchIndicatorsPrivate = async () => {
  const res = await apiAdmin.get(API_BASE_INDICATORS_PRIVATE);
  return res.data || { count: 0, files: [], data: [] };
};

export const deleteIndicator = async (id) => {
  return apiAdmin.delete(`${API_BASE_INDICATORS_PRIVATE}/${id}`);
};

/* ================= INDICATORS (PUBLIC) ================= */

export const fetchIndicatorsPublic = async () => {
  const res = await axios.get(API_BASE_INDICATORS_PUBLIC);
  return res.data || { count: 0, files: [], data: [] };
};

/* ================= FILE ACTIONS (ADMIN) ================= */

export const deleteFile = async (fileId, type) => {
  await apiAdmin.delete(
    `${API_BASE_FILES}/${fileId}${
      type ? `?type=${encodeURIComponent(type)}` : ""
    }`
  );
};

export const deleteAllFiles = async (type) => {
  const cleanType =
    typeof type === "string" ? type.trim().toLowerCase() : type;

  return apiAdmin.delete(
    `${API_BASE_FILES}/delete-all${
      cleanType ? `?type=${encodeURIComponent(cleanType)}` : ""
    }`
  );
};

/* ================= DOWNLOAD / PREVIEW (ADMIN) ================= */

export const downloadFile = async (fileId, type) => {
  const res = await apiAdmin.get(
    `${API_BASE_FILES}/${fileId}/download?type=${encodeURIComponent(type)}`,
    { responseType: "blob" }
  );

  let filename = "fichier_download";
  const disposition = res.headers["content-disposition"];

  if (disposition) {
    let match = disposition.match(/filename\*=UTF-8''([^;]+)/);
    if (match?.[1]) filename = decodeURIComponent(match[1]);
    else {
      match = disposition.match(/filename="([^"]+)"/);
      if (match?.[1]) filename = match[1];
    }
  }

  const blob = new Blob([res.data], {
    type: res.headers["content-type"],
  });

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const previewFile = async (fileId, type) => {
  const res = await apiAdmin.get(
    `${API_BASE_FILES}/${fileId}/download?type=${encodeURIComponent(type)}`,
    { responseType: "blob" }
  );

  const blob = new Blob([res.data], {
    type: res.headers["content-type"],
  });

  return window.URL.createObjectURL(blob);
};

/* ================= ELASTICSEARCH (ADMIN) ================= */
export async function fetchDocuments(filters = {}) { 

  
  const params = new URLSearchParams();
  if (filters.indicator) params.append("indicator", filters.indicator);
  if (filters.year) params.append("year", filters.year.toString());
  if (filters.filename) params.append("filename", filters.filename);
  if (filters.page) params.append("page", filters.page.toString());
  if (filters.page_size) params.append("page_size", filters.page_size.toString());
  const res = await apiAdmin.get(`${API_BASE_ES}/documents?${params.toString()}`);
  return res.data;
}

export async function deleteDocument(id) {
  return apiAdmin.delete(`${API_BASE_ES}/document/${id}`);
}

export async function deleteAllDocuments() {
  return apiAdmin.delete(`${API_BASE_ES}/documents/all`);
}
