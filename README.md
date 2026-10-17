# ESG Multi-Agent Project — Day 1 Setup

Follow these steps in order. Total time: ~30–60 minutes (API key approval can take longer, so start that first).

## Step 0 — Get your API key first (it may take time to process)
1. Go to https://dashscope.console.aliyun.com/
2. Create/log into an Alibaba Cloud account.
3. Go to "API Key Management" → generate a new key.
4. Keep this key somewhere safe — you'll paste it into `.env` in Step 3.

## Step 1 — Create your GitHub repo
```bash
mkdir esg-multi-agent-project
cd esg-multi-agent-project
git init
git remote add origin <your-empty-github-repo-url>
```
Copy all files from this starter kit into that folder.

## Step 2 — Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 3 — Add your API key
```bash
cp .env.example .env
```
Open `.env` and replace `your-api-key-here` with the real key from Step 0.
(`.env` is already in `.gitignore` so it won't be committed.)

## Step 4 — Verify the API works
```bash
python test_qwen_api.py
```
If you see a generated paragraph printed to your terminal, you're done with Day 1.
If you get an error, double check the key was copied correctly and that there's no
extra whitespace in `.env`.

## Step 5 — First commit
```bash
git add .
git commit -m "Day 1: project setup and API verification"
git push -u origin main
```

## What's next (Week 1, remaining steps)
- Read GRI Universal Standards (GRI 1, 2, 3) and build a spreadsheet of material
  topics under Environmental / Social / Governance.
- Read the TCFD recommendations and map its 4 pillars (Governance, Strategy,
  Risk Management, Metrics & Targets) to your GRI topic list.

These two don't need the API and can be done while your DashScope account is
being approved.
