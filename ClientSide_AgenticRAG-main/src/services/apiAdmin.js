import axios from "axios";

const apiAdmin = axios.create({
  baseURL: "/api/admin",
});

apiAdmin.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiAdmin;
