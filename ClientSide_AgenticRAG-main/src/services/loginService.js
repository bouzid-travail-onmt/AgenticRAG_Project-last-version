// src/services/loginService.js
import axios from "axios";

const API_BASE_URL = "/api/auth"; // ✅ Base de ton backend
// 🔹 Fonction de connexion utilisateur
export async function login(username, password) {
  try {
    // Formulaire encodé comme FastAPI (OAuth2PasswordRequestForm)
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    // 🔹 Requête POST vers /login
    const response = await axios.post(`${API_BASE_URL}/login`, formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    // ✅ Sauvegarder le token JWT + infos utilisateur dans le localStorage
    localStorage.setItem("token", response.data.access_token);
    localStorage.setItem("username", response.data.username);
    localStorage.setItem("role", response.data.role);

    return response.data;
  } catch (error) {
    console.error("❌ Erreur login:", error.response?.data || error.message);
    throw error.response?.data || error;
  }
}

// 🔹 Fonction pour générer les headers d’authentification
export function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// 🔹 Fonction utilitaire pour vérifier si un utilisateur est connecté
export function isAuthenticated() {
  return !!localStorage.getItem("token");
}

// 🔹 Fonction pour se déconnecter proprement
export async function logout() {
  const token = localStorage.getItem("token");
  if (token) {
    try {
      await axios.post(`${API_BASE_URL}/logout`, null, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) {
      console.error("❌ Erreur déconnexion:", error.response?.data || error.message);
    }
  }
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  localStorage.removeItem("role");
}
