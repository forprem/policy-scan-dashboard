import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000"
});

export const scanSite = (url) =>
  API.post("/scan", { url });

// NEW Code Scan
export const scanRepo = (repo, pat) =>
  API.post("/scan-repo", { repo, pat });