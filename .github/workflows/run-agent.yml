name: HN Content Agent

on:
  schedule:
    - cron: '0 14 * * 2'
    - cron: '0 14 * * 5'
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run HN Content Agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ZAPIER_WEBHOOK: ${{ secrets.ZAPIER_WEBHOOK }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          REPLICATE_API_KEY: ${{ secrets.REPLICATE_API_KEY }}
          CLOUDINARY_CLOUD: ${{ secrets.CLOUDINARY_CLOUD }}
          CLOUDINARY_API_KEY: ${{ secrets.CLOUDINARY_API_KEY }}
          CLOUDINARY_SECRET: ${{ secrets.CLOUDINARY_SECRET }}
          ZAPIER_LIBRARY_HOOK: ${{ secrets.ZAPIER_LIBRARY_HOOK }}
        run: python agent.py
