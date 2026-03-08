---
name: flyweel-engine-setup
description: Expert guide for setting up and configuring the FLYWEEL-AGENTIC-CONTENT-ENGINE repository. Use when a user asks for help setting up the project, installing dependencies, configuring API keys, or customizing the brand configuration files.
---

# Flyweel Engine Setup Guide

## Overview

This skill provides the exact workflow to help a user set up the `FLYWEEL-AGENTIC-CONTENT-ENGINE` from scratch. The setup process involves configuring environment variables (API keys), modifying the generic "Acme" branding config files to match the user's actual brand, and verifying the installation.

## Workflow Decision Tree

When a user asks to "set up the repo" or "help me install", follow these steps in order:

### Step 1: Python Environment & Dependencies
1. Check if a virtual environment exists (`venv/` or `.venv/`).
2. If not, ask the user if they'd like you to create one (`python -m venv venv` and `source venv/bin/activate`).
3. Install dependencies: `pip install -r requirements.txt`.

### Step 2: API Keys & Environment Variables
1. Check if `.env` exists. If not, copy `.env.example` to `.env`.
2. The engine requires several API keys to function fully (Google Gemini, Groq, Perplexity, and optionally Nebius for BYOK).
3. **Important Security Rule**: NEVER ask the user to paste their raw API keys into the chat. Instead, instruct them to open the `.env` file and paste the keys themselves, OR provide a script/command they can run locally to inject them.
4. You can run the validation script in `API_KEYS_SETUP.md` to check which keys are currently configured (without printing the keys themselves).

### Step 3: Brand Configuration (`config/` directory)
The project ships with generic "Acme" branding. The user needs to customize these.
Ask the user for their:
- **Brand Name** (e.g., "My SaaS Co")
- **Target Audience / ICP** (e.g., "B2B SaaS Founders")
- **Main Product/Service** 
- **Author Profile** (e.g., Name and role of the primary author)

Once the user provides this context, use the `replace` or `write_file` tools to update the following critical files:
- `config/author_profiles.json`: Update "Jane Doe" and "Acme" references.
- `config/brand_voice_config.json`: Adjust tone and style rules.
- `config/products.json`: Replace the generic "Acme Widget" with their actual product details.
- `config/icp_config.json`: Update the target audience.

### Step 4: System Paths
1. Ask the user where their output Astro/Markdown site is located.
2. Instruct them to add `ASTRO_SITE_PATH=/path/to/their/site` to the `.env` file so the `core/publisher.py` knows where to write the generated content. If they don't have one, it defaults to `../my-astro-site`.

### Step 5: Verification
1. Run `pytest tests/quick_test.py` to ensure the basic imports and components are working.
2. Provide them with a sample command to generate their first article:
   ```bash
   python generate.py -k "your target keyword" --nb
   ```

## Best Practices
- **Do not read all config files at once** to save context window. Read them individually when you are ready to update them.
- **Do not print secrets**. If you need to verify `.env`, use `grep` or `cat` piped to commands that only show the keys exist, not their values.
- **Be proactive but safe**: Offer to run the sed/replace commands for the config files once the user gives you their brand details.
