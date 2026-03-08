# API Keys Setup Guide

This guide explains how to obtain and configure API keys for the V2 Brand Content Engine.

## Quick Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys (see instructions below)

3. **Never commit the `.env` file to git** (already in .gitignore)

---

## Required API Keys

### 1. Google AI (Gemini) - `GOOGLE_API_KEY`

**Purpose**: Content generation using Gemini 3 Flash

**How to get it**:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add to `.env`:
   ```
   GOOGLE_API_KEY=AIza...
   ```

**Pricing**: Free tier available, then pay-as-you-go

---

### 2. Groq - `GROQ_API_KEY`

**Purpose**: Fast inference for community mining and content refinement

**How to get it**:
1. Go to [Groq Console](https://console.groq.com/keys)
2. Sign up or log in
3. Create a new API key
4. Copy the key and add to `.env`:
   ```
   GROQ_API_KEY=gsk_...
   ```

**Pricing**: Free tier with rate limits, paid plans available

---

### 3. Perplexity - `PERPLEXITY_API_KEY`

**Purpose**: SERP analysis, web research, and PAA questions

**How to get it**:
1. Go to [Perplexity Settings](https://www.perplexity.ai/settings/api)
2. Sign in to your account
3. Navigate to API section
4. Generate a new API key
5. Copy the key and add to `.env`:
   ```
   PERPLEXITY_API_KEY=pplx-...
   ```

**Pricing**: Pay-per-use, starts at $0.001 per request

---

## Optional API Keys

### 4. Nebius (OpenAI-compatible) - `NEBIUS_API_KEY`

**Purpose**: Content polishing and humanization (using Llama 3.3 70B or Qwen3 235B)

**How to get it**:
1. Go to [Nebius Console](https://console.studio.nebius.com)
2. Create an account
3. Navigate to API Keys section
4. Generate a new key
5. Copy the key and add to `.env`:
   ```
   NEBIUS_API_KEY=your_key_here
   ```

**Note**: If not configured, the polish step will be skipped (content will still be generated)

**Pricing**: Pay-per-token, competitive pricing

---

### 5. Google Search Console - `GOOGLE_SERVICE_ACCOUNT_PATH`

**Purpose**: Keyword research from your own site's search data (optional)

**How to get it**:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a service account
3. Download the JSON credentials file
4. Add path to `.env`:
   ```
   GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
   GSC_SITE_URL=https://your-site.com
   ```

**Note**: Only needed if you want to use GSC data for keyword research

---

## CI/CD Setup (GitHub Actions)

For GitHub Actions to run tests, add the following secrets to your repository:

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each key:
   - `GOOGLE_API_KEY`
   - `GROQ_API_KEY`
   - `PERPLEXITY_API_KEY`
   - `NEBIUS_API_KEY` (optional)

**Important**: Never expose API keys in logs or commit them to the repository.

---

## Validation

### Local Development

Check if your keys are working:

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

keys = {
    'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
    'GROQ_API_KEY': os.getenv('GROQ_API_KEY'),
    'PERPLEXITY_API_KEY': os.getenv('PERPLEXITY_API_KEY'),
    'NEBIUS_API_KEY': os.getenv('NEBIUS_API_KEY')
}

for name, key in keys.items():
    status = '✓' if key else '✗'
    print(f'{status} {name}: {\"configured\" if key else \"missing\"}')"
```

### CI/CD

Integration tests will automatically:
- ✅ Run if all required keys are present
- ⏭️ Skip gracefully if keys are missing
- 📊 Report which keys are configured

---

## Security Best Practices

1. **Never commit** `.env` to git (already in `.gitignore`)
2. **Rotate keys** regularly
3. **Use different keys** for dev/staging/production
4. **Monitor usage** to detect unauthorized access
5. **Revoke compromised keys** immediately

---

## Cost Optimization

### Estimated costs per article (with all features):
- **Perplexity**: ~$0.03 (SERP + PAA)
- **Groq**: ~$0.02 (Reddit/Quora mining + refinement)
- **Gemini**: ~$0.05 (content generation)
- **Nebius**: ~$0.01 (polish step)

**Total**: ~$0.11 per article

### Cost reduction options:

1. **Skip community research** (`--nr` flag):
   ```bash
   python generate.py -k "keyword" --nr  # Saves ~$0.02
   ```

2. **Limited community insights** (`--nrl` flag):
   ```bash
   python generate.py -k "keyword" --nrl  # Uses 3 Reddit + 1 Quora only
   ```

3. **Skip polish step** (don't configure `NEBIUS_API_KEY`):
   - Saves ~$0.01 per article
   - Content still high quality, just less humanized

---

## Troubleshooting

### Error: "Gemini client not initialized - check GOOGLE_API_KEY"
- Ensure `GOOGLE_API_KEY` is set in `.env`
- Check the key is valid (no extra spaces or quotes)
- Verify you've enabled the Gemini API in Google Cloud

### Error: "No Groq key"
- Add `GROQ_API_KEY` to `.env`
- Verify the key format starts with `gsk_`

### Error: "No Perplexity key"
- Add `PERPLEXITY_API_KEY` to `.env`
- Ensure your Perplexity account has API access enabled

### Integration tests skipped in CI
- Add API keys to GitHub repository secrets
- Ensure secret names match exactly (case-sensitive)
- Check workflow logs for specific missing keys

---

## Questions?

- 📧 Contact: hello@acme.com
- 📚 Docs: See README.md
- 🐛 Issues: GitHub Issues
