import yt_dlp
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

@csrf_exempt
def fetch_video_info(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            url = data.get("url")

            if not url:
                return JsonResponse({"error": "No URL provided"}, status=400)

            # Set up yt-dlp options
            ydl_opts = {
                "format": "best[ext=mp4]",
                "noplaylist": True,  # Don't download entire playlists
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info.get("url")
                if not video_url:
                    video_url = info.get("formats")[0]["url"]
                title = info["title"]

            return JsonResponse({"title": title, "video_url": video_url})

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Failed to fetch video info: {e}")
            return JsonResponse({"error": "Failed to fetch video info", "details": str(e)}, status=500)

        except Exception as e:
            logger.error(f"Internal server error: {e}")
            return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)

    # ✅ Handle GET requests properly
    return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
