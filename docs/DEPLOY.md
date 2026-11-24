# Deploy guide

The service is one Docker container. It needs no database. Both options below give you a public link for the README.

Before you deploy, decide on the API key:
- **No key:** the service runs in rule mode. This is fine for a demo.
- **With key:** add `OPENAI_API_KEY` as a secret in the host settings. Never put it in the code or in `.env.example`.

Because the API has no login, anyone with the link can use it and spend your LLM credit. For a public demo, either leave the key empty or set a low spending limit at your LLM provider.

## Option A: Render (free, easiest)

1. Push the repo to GitHub.
2. Go to render.com and sign in with GitHub.
3. Click **New > Blueprint** and choose this repo. Render reads `render.yaml`.
4. Fill in the secret values you want (all can stay empty), then click **Apply**.
5. Wait for the build. Open the URL. `/health` should show `"status": "ok"`.

Free Render services sleep after a period with no traffic, so the first request can take about a minute.

## Option B: Azure Container Apps

Needs the Azure CLI and an Azure account. These commands were written from the Azure CLI docs and not run for this repo, so check the output of each step.

```bash
az login
az group create --name rg-scoping --location centralindia
az containerapp up \
  --name scoping-tool \
  --resource-group rg-scoping \
  --location centralindia \
  --source . \
  --ingress external \
  --target-port 8000
```

Add secrets and settings:

```bash
az containerapp secret set -n scoping-tool -g rg-scoping --secrets openai-key=YOUR_KEY
az containerapp update -n scoping-tool -g rg-scoping \
  --set-env-vars OPENAI_API_KEY=secretref:openai-key LLM_MODEL=gpt-4o-mini
```

The command prints the public URL. Delete everything when you are done to avoid charges:

```bash
az group delete --name rg-scoping
```

## After deploying

1. Open the URL and try the sample from the page.
2. Put the URL in the README under **Live demo**.
3. Record a short screen video (about 2 minutes): paste a transcript, show the flagged items and open questions, upload the sample PDF.
