# YouTube Key Ideas

A local Python service and Chrome extension for summarizing the key ideas from the current YouTube video.

The Chrome extension injects a summary panel into YouTube. The backend service extracts the transcript with `youtube-transcript-api` and calls DeepSeek. The DeepSeek API key stays on the backend.

## Start The Service

From the project root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DEEPSEEK_API_KEY="your-deepseek-api-key"
python3 service.py
```

The service runs at:

```text
http://127.0.0.1:5012
```

Open that URL in a browser to view saved summaries.

Optional model override:

```bash
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

Health check:

```bash
curl http://127.0.0.1:5012/health
```

## Load The Chrome Extension

1. Open Chrome and go to `chrome://extensions`.
2. Turn on `Developer mode`.
3. Click `Load unpacked`.
4. Select the `chrome/` folder in this project.
5. Open a YouTube video.
6. Click the `YouTube Key Ideas` extension action.

The extension will open a right-side panel on the YouTube page and render the summary returned by the local service.
Each successful extraction is saved as a JSON file under `data/summaries/`.

## API

```bash
curl -X POST http://127.0.0.1:5012/key-ideas \
  -H "content-type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Saved summaries:

```bash
curl http://127.0.0.1:5012/summaries
curl http://127.0.0.1:5012/summaries/VIDEO_ID
```
