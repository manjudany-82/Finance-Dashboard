# 🚀 Deployment Guide: Financial Dashboard Enterprise

This guide outlines the steps to take your **Financial Dashboard** from development to a live production environment.

## 1. Prerequisites

Ensure you have the following ready:
*   **Source Code**: The contents of the `financial-analyzer` folder.
*   **Environment Variables**: A `.env` file or cloud secrets containing:
    *   `GEMINI_API_KEY`: For AI Insights.
    *   `AZURE_CLIENT_ID`: (If using advanced OneDrive auth).

## 2. Option A: Streamlit Community Cloud (Easiest)

Best for quick sharing and demos.

1.  Push your code to a public **GitHub** repository.
2.  Log in to [Streamlit Cloud](https://streamlit.io/cloud).
3.  Click **"New App"** and select your repository & branch.
4.  **Main file path**: `dashboard.py`.
5.  **Advanced Settings**:
    *   Add your `GEMINI_API_KEY` in the "Secrets" section.
6.  Click **Deploy**.

## 3. Option B: Docker (Enterprise Standard)

Best for internal deployment, security, and stability.

### 3.1 Build the Image
```bash
docker build -t financial-dashboard .
```

### 3.2 Run the Container
```bash
docker run -p 8501:8501 --env-file .env financial-dashboard
```
Access the app at `http://localhost:8501`.

### 3.3 Docker Compose
We have included a `docker-compose.yml` for easier management.
```bash
docker-compose up -d --build
```

## 4. Option C: Cloud Platforms (Railway / Render / Azure)

Best for persistent hosting with minimal DevOps.

### Deploying to Render
1.  Connect your GitHub repo to **Render**.
2.  Select **"Web Service"**.
3.  **Environment**: Docker.
4.  **Region**: Choose closest to you.
5.  **Environment Variables**: Add `GEMINI_API_KEY`.
6.  Click **Create Web Service**.

### Deploying to Azure App Service
1.  Push your Docker image to **Azure Container Registry (ACR)**.
2.  Create a **Web App for Containers** in Azure Portal.
3.  Select your image from ACR.
4.  Configure App Settings (Environment Variables) in the Azure Portal.

## ⚠️ Production Checklist before "Go Live"

*   [ ] **Security**: Ensure `debug=False` (Streamlit default in prod) and secrets are NOT committed to git.
*   [ ] **Dependencies**: `requirements.txt` is frozen (already done).
*   [ ] **Data**: Ensure the `financial_template.xlsx` is available in the root folder so users can download it.
*   [ ] **Performance**: If using large datasets, consider caching via `@st.cache_data`.

---
**Version**: 1.1.0 Enterprise
**Maintainer**: Gravity Team
