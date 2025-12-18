# 🔒 Client Authentication Setup Guide

## Overview
Your dashboard now requires login credentials. Only users you authorize can access the financial data.

## Setting Up Client Access

### Step 1: Generate Password Hash

Run the password generator:
```powershell
python generate_password_hash.py
```

Enter your client's password when prompted. Copy the generated hash.

### Step 2: Configure Secrets

**For Local Development:**
1. Create `.streamlit/secrets.toml` (copy from `.streamlit/secrets.toml.example`)
2. Add your client's credentials:

```toml
[users]
client_name = "paste_hash_here"
another_client = "paste_another_hash_here"

GEMINI_API_KEY = "your-api-key"
ONEDRIVE_LINK = "your-onedrive-link"
```

**For Streamlit Cloud:**
1. Go to your app settings on share.streamlit.io
2. Navigate to **Secrets**
3. Paste the same content as above

### Step 3: Share Credentials with Client

Send your client:
- **URL**: `https://your-app.streamlit.app` (or `http://192.168.0.8:8501` for local)
- **Username**: `client_name`
- **Password**: The original password (NOT the hash)

## Adding Multiple Clients

You can add as many clients as needed:

```toml
[users]
client_a = "hash_for_client_a"
client_b = "hash_for_client_b"
client_c = "hash_for_client_c"
```

Each client gets their own username and password.

## Security Features

✅ **Passwords are hashed** - Never stored in plain text
✅ **Private GitHub repo** - Code is not public
✅ **Secrets management** - Credentials stored securely
✅ **Session-based** - Login persists during session

## Revoking Access

To remove a client's access:
1. Delete their line from `secrets.toml`
2. Save and redeploy (Streamlit Cloud auto-redeploys)

## Example Workflow

1. Client visits your dashboard URL
2. Sees login screen
3. Enters their username and password
4. Gets access to all financial data
5. Can use dashboard normally

---

**Need help?** The authentication is already integrated and working!
