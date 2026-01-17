---
applyTo: '**/*.py'
description: 'Env file use instructions for Python projects'
---

# Env usage rule

Always load API keys and other secrets from a `.env` file (or the process environment) instead of hardcoding them in source.

- Add `.env` to `.gitignore` and never commit secrets.
- Recommended package: `python-dotenv` (pip install python-dotenv).
- Load at application startup (example):

```py
from dotenv import load_dotenv
import os

load_dotenv()  # merges .env into environment variables
API_KEY = os.getenv('API_KEY')
SECRET = os.getenv('SECRET')
if not API_KEY or not SECRET:
    raise RuntimeError('Missing required environment variables')
```

- For production, prefer a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.) and set environment variables from the deployment system instead of shipping a `.env` file.

This rule applies to all Python files matching the `applyTo` pattern above.
