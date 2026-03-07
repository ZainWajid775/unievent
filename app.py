import os
import json
import boto3
import requests
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from botocore.exceptions import ClientError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
S3_BUCKET        = os.environ.get("S3_BUCKET", "unievent-media-bucket")
AWS_REGION       = os.environ.get("AWS_REGION", "us-east-1")
TICKETMASTER_KEY = os.environ.get("TICKETMASTER_API_KEY", "")
EVENTS_JSON_KEY  = "events/latest_events.json"

s3 = boto3.client("s3", region_name=AWS_REGION)

# ─── Fetch events from Ticketmaster API ───────────────────────────────────────
def fetch_events_from_api():
    """Fetch events from Ticketmaster Discovery API and store in S3."""
    if not TICKETMASTER_KEY:
        logger.warning("No Ticketmaster API key set — using mock data.")
        return _mock_events()

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey":        TICKETMASTER_KEY,
        "classificationName": "music,sports,arts",
        "size":          20,
        "sort":          "date,asc",
        "countryCode":   "US",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        events = _parse_ticketmaster(raw)
        _save_events_to_s3(events)
        logger.info(f"Fetched & stored {len(events)} events from Ticketmaster.")
        return events
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return _load_events_from_s3()

def _parse_ticketmaster(raw):
    items = raw.get("_embedded", {}).get("events", [])
    events = []
    for item in items:
        venue = {}
        if item.get("_embedded", {}).get("venues"):
            v = item["_embedded"]["venues"][0]
            venue = {
                "name":    v.get("name", "TBA"),
                "city":    v.get("city", {}).get("name", ""),
                "country": v.get("country", {}).get("name", ""),
            }
        images = item.get("images", [])
        image_url = images[0]["url"] if images else ""
        dates = item.get("dates", {}).get("start", {})
        events.append({
            "id":          item.get("id"),
            "title":       item.get("name", "Untitled Event"),
            "date":        dates.get("localDate", "TBA"),
            "time":        dates.get("localTime", ""),
            "venue":       venue,
            "description": item.get("info", item.get("pleaseNote", "No description available.")),
            "image_url":   image_url,
            "url":         item.get("url", "#"),
            "genre":       item.get("classifications", [{}])[0].get("genre", {}).get("name", "General"),
        })
    return events

def _save_events_to_s3(events):
    payload = json.dumps({"fetched_at": datetime.utcnow().isoformat(), "events": events})
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=EVENTS_JSON_KEY,
        Body=payload,
        ContentType="application/json",
    )

def _load_events_from_s3():
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=EVENTS_JSON_KEY)
        data = json.loads(obj["Body"].read())
        return data.get("events", [])
    except ClientError:
        logger.warning("No cached events in S3 — returning mock data.")
        return _mock_events()

def _mock_events():
    return [
        {
            "id": "mock-001",
            "title": "Annual Science & Technology Fest",
            "date": "2025-09-15",
            "time": "10:00:00",
            "venue": {"name": "Main Auditorium", "city": "Topi", "country": "Pakistan"},
            "description": "Showcase your projects and innovations at GIKI's biggest tech festival.",
            "image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600",
            "url": "#",
            "genre": "Technology",
        },
        {
            "id": "mock-002",
            "title": "Inter-University Sports Gala",
            "date": "2025-10-05",
            "time": "09:00:00",
            "venue": {"name": "Sports Complex", "city": "Topi", "country": "Pakistan"},
            "description": "Compete in cricket, football, basketball and more against top universities.",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600",
            "url": "#",
            "genre": "Sports",
        },
        {
            "id": "mock-003",
            "title": "Cultural Night 2025",
            "date": "2025-11-20",
            "time": "18:00:00",
            "venue": {"name": "Open Amphitheatre", "city": "Topi", "country": "Pakistan"},
            "description": "A night of music, dance, and cultural performances by GIKI students.",
            "image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600",
            "url": "#",
            "genre": "Arts",
        },
    ]

# ─── Upload poster to S3 ───────────────────────────────────────────────────────
def upload_poster_to_s3(file_obj, filename):
    key = f"posters/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    s3.upload_fileobj(
        file_obj, S3_BUCKET, key,
        ExtraArgs={"ContentType": "image/jpeg", "ACL": "private"},
    )
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return url

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    events = _load_events_from_s3()
    return render_template("index.html", events=events, now=datetime.utcnow())

@app.route("/api/events")
def api_events():
    events = _load_events_from_s3()
    return jsonify({"status": "ok", "count": len(events), "events": events})

@app.route("/api/events/refresh", methods=["POST"])
def api_refresh():
    events = fetch_events_from_api()
    return jsonify({"status": "ok", "count": len(events), "message": "Events refreshed."})

@app.route("/api/upload-poster", methods=["POST"])
def upload_poster():
    if "poster" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["poster"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    url = upload_poster_to_s3(f, f.filename)
    return jsonify({"status": "ok", "url": url})

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

# ─── Scheduler: refresh every 6 hours ─────────────────────────────────────────
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_events_from_api, "interval", hours=6)
scheduler.start()

if __name__ == "__main__":
    fetch_events_from_api()          # initial load
    app.run(host="0.0.0.0", port=5000, debug=False)
