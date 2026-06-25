#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi


PORT = 5012
DEFAULT_MODEL = "deepseek-v4-flash"
MAX_TRANSCRIPT_CHARS = 100_000
ROOT_DIR = Path(__file__).resolve().parent
INDEX_PATH = ROOT_DIR / "index.html"
SUMMARY_DIR = ROOT_DIR / "data" / "summaries"


class ServiceError(Exception):
  def __init__(self, message, status=400):
    super().__init__(message)
    self.status = status


def fetch_text(url, headers=None):
  req = urllib.request.Request(
    url,
    headers={
      "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
      ),
      **(headers or {}),
    },
  )
  try:
    with urllib.request.urlopen(req, timeout=30) as response:
      return response.read().decode("utf-8", errors="replace")
  except urllib.error.HTTPError as e:
    raise ServiceError(f"Request failed for {url} ({e.code}).", e.code)
  except urllib.error.URLError as e:
    raise ServiceError(f"Could not reach {url}: {e.reason}.", 502)


def post_json(url, payload, headers=None):
  data = json.dumps(payload).encode("utf-8")
  req = urllib.request.Request(
    url,
    data=data,
    method="POST",
    headers={
      "content-type": "application/json",
      **(headers or {}),
    },
  )
  try:
    with urllib.request.urlopen(req, timeout=90) as response:
      body = response.read().decode("utf-8", errors="replace")
      return response.status, body
  except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    return e.code, body
  except urllib.error.URLError as e:
    raise ServiceError(f"Could not reach DeepSeek: {e.reason}.", 502)


def extract_json_object(text, marker):
  index = text.find(marker)
  if index == -1:
    return None

  start = text.find("{", index)
  if start == -1:
    return None

  depth = 0
  in_string = False
  escape = False

  for offset in range(start, len(text)):
    char = text[offset]
    if in_string:
      if escape:
        escape = False
      elif char == "\\":
        escape = True
      elif char == '"':
        in_string = False
    else:
      if char == '"':
        in_string = True
      elif char == "{":
        depth += 1
      elif char == "}":
        depth -= 1
        if depth == 0:
          return text[start : offset + 1]

  return None


def validate_youtube_url(url):
  parsed = urllib.parse.urlparse(url)
  host = parsed.netloc.lower()
  if host.startswith("www."):
    host = host[4:]

  if host == "youtube.com" and parsed.path == "/watch":
    video_id = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
  elif host == "youtu.be":
    video_id = parsed.path.strip("/")
  else:
    raise ServiceError("Provide a valid YouTube video URL.")

  if not re.fullmatch(r"[\w-]{11}", video_id):
    raise ServiceError("Could not read a valid YouTube video id from the URL.")

  return video_id, f"https://www.youtube.com/watch?v={video_id}"


def get_thumbnail_url(video_id):
  return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def fetch_title(video_url):
  page_html = fetch_text(video_url)
  raw_player = extract_json_object(page_html, "ytInitialPlayerResponse")
  if not raw_player:
    return ""

  try:
    player = json.loads(raw_player)
  except json.JSONDecodeError:
    return ""

  return player.get("videoDetails", {}).get("title", "")


def extract_transcript(video_id, video_url):
  try:
    fetched = YouTubeTranscriptApi().fetch(video_id)
  except Exception as e:
    raise ServiceError(f"Could not fetch transcript: {e}")

  parts = [snippet.text for snippet in fetched if snippet.text]
  transcript = re.sub(r"\s+", " ", " ".join(parts)).strip()
  if not transcript:
    raise ServiceError("Transcript was empty.")

  title = fetch_title(video_url)
  return title, transcript


def get_key_ideas(title, transcript):
  api_key = os.environ.get("DEEPSEEK_API_KEY")
  if not api_key:
    raise ServiceError("DEEPSEEK_API_KEY is not set in the backend environment.", 500)

  prompt = (
    "Extract the key ideas from this YouTube video transcript.\n\n"
    f"Title: {title}\n\n"
    "Return:\n"
    "- A 2-sentence summary\n"
    "- 5-8 key takeaways as bullets\n"
    "- Any notable quotes, numbers, or claims worth remembering\n\n"
    f"Transcript:\n{transcript[:MAX_TRANSCRIPT_CHARS]}"
  )

  status, body = post_json(
    "https://api.deepseek.com/chat/completions",
    {
      "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
      "max_tokens": 1500,
      "messages": [{"role": "user", "content": prompt}],
    },
    {"authorization": f"Bearer {api_key}"},
  )

  if not body:
    raise ServiceError(f"DeepSeek returned an empty response ({status}).", 502)

  try:
    data = json.loads(body)
  except json.JSONDecodeError:
    raise ServiceError(f"DeepSeek returned invalid JSON: {body[:300]}", 502)

  if data.get("error"):
    message = data["error"].get("message", "Unknown DeepSeek error.")
    raise ServiceError(f"DeepSeek API error: {message}", 502)
  if status < 200 or status >= 300:
    raise ServiceError(f"DeepSeek request failed ({status}).", 502)

  key_ideas = (
    data.get("choices", [{}])[0]
    .get("message", {})
    .get("content", "")
    .strip()
  )
  if not key_ideas:
    raise ServiceError("DeepSeek returned an empty summary.", 502)

  return key_ideas


def summary_path(video_id):
  return SUMMARY_DIR / f"{video_id}.json"


def save_summary(record):
  SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
  path = summary_path(record["videoId"])
  temp_path = path.with_suffix(".json.tmp")
  temp_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
  temp_path.replace(path)


def read_summary(video_id):
  if not re.fullmatch(r"[\w-]{11}", video_id):
    raise ServiceError("Invalid video id.")

  path = summary_path(video_id)
  if not path.exists():
    raise ServiceError("Summary not found.", 404)

  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except json.JSONDecodeError:
    raise ServiceError("Saved summary is not valid JSON.", 500)


def list_summaries():
  if not SUMMARY_DIR.exists():
    return []

  summaries = []
  for path in SUMMARY_DIR.glob("*.json"):
    try:
      item = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      continue

    summaries.append(
      {
        "videoId": item.get("videoId"),
        "url": item.get("url"),
        "title": item.get("title") or "Untitled video",
        "thumbnail": item.get("thumbnail"),
        "transcriptLength": item.get("transcriptLength", 0),
        "createdAt": item.get("createdAt", ""),
      }
    )

  return sorted(summaries, key=lambda item: item.get("createdAt", ""), reverse=True)


class Handler(BaseHTTPRequestHandler):
  def end_headers(self):
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "content-type")
    super().end_headers()

  def do_OPTIONS(self):
    self.send_response(204)
    self.end_headers()

  def do_GET(self):
    parsed = urllib.parse.urlparse(self.path)
    path = parsed.path

    if path == "/":
      self.write_file(INDEX_PATH, "text/html; charset=utf-8")
      return
    if path in ("/marked.umd.js", "/chrome/marked.umd.js"):
      self.write_file(ROOT_DIR / "chrome" / "marked.umd.js", "text/javascript; charset=utf-8")
      return
    if path == "/favicon.ico":
      self.write_empty(204, "image/x-icon")
      return
    if path == "/health":
      self.write_json(200, {"ok": True})
      return
    if path == "/summaries":
      self.write_json(200, {"ok": True, "summaries": list_summaries()})
      return
    if path.startswith("/summaries/"):
      video_id = path.removeprefix("/summaries/")
      try:
        self.write_json(200, {"ok": True, "summary": read_summary(video_id)})
      except ServiceError as e:
        self.write_json(e.status, {"ok": False, "error": str(e)})
      return

    self.write_json(404, {"ok": False, "error": "Not found."})

  def do_POST(self):
    if self.path != "/key-ideas":
      self.write_json(404, {"ok": False, "error": "Not found."})
      return

    try:
      content_length = int(self.headers.get("content-length", "0"))
      raw_body = self.rfile.read(content_length).decode("utf-8")
      payload = json.loads(raw_body or "{}")
      video_id, video_url = validate_youtube_url(payload.get("url", ""))
      title, transcript = extract_transcript(video_id, video_url)
      key_ideas = get_key_ideas(title, transcript)
      record = {
        "videoId": video_id,
        "url": video_url,
        "title": title or "Untitled video",
        "thumbnail": get_thumbnail_url(video_id),
        "transcriptLength": len(transcript),
        "keyIdeas": key_ideas,
        "createdAt": datetime.now(timezone.utc).isoformat(),
      }
      save_summary(record)
      self.write_json(
        200,
        {
          "ok": True,
          **record,
        },
      )
    except json.JSONDecodeError:
      self.write_json(400, {"ok": False, "error": "Request body must be valid JSON."})
    except ServiceError as e:
      self.write_json(e.status, {"ok": False, "error": str(e)})
    except Exception as e:
      print(f"Unexpected error: {e}", file=sys.stderr)
      self.write_json(500, {"ok": False, "error": "Unexpected backend error."})

  def write_json(self, status, payload):
    body = json.dumps(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("content-type", "application/json")
    self.send_header("content-length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def write_file(self, path, content_type):
    if not path.exists():
      self.write_json(404, {"ok": False, "error": "Not found."})
      return

    body = path.read_bytes()
    self.send_response(200)
    self.send_header("content-type", content_type)
    self.send_header("content-length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def write_empty(self, status, content_type):
    self.send_response(status)
    self.send_header("content-type", content_type)
    self.send_header("content-length", "0")
    self.end_headers()

  def log_message(self, fmt, *args):
    print(f"{self.address_string()} - {fmt % args}")


def main():
  server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
  print(f"yt-key-ideas service running at http://127.0.0.1:{PORT}")
  server.serve_forever()


if __name__ == "__main__":
  main()
