import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL;

const API = axios.create({
  // baseURL: "http://localhost:8000"
  baseURL: API_BASE_URL
});

export const scanSite = (url) =>
  API.post("/scan", { url });

// NEW Code Scan
export const scanRepo = (repo, pat) =>
  API.post("/scan-repo", { repo, pat });
