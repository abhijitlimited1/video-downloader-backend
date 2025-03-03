import yt_dlp
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import json
import logging
import requests

logger = logging.getLogger(__name__)

def generate_stream(response):
    """Stream video in chunks"""
    for chunk in response.iter_content(chunk_size=8192):
        yield chunk

@require_GET
def stream_video(request):
    """Stream video from source"""
    video_url = request.GET.get("url")
    title = request.GET.get("title", "video")

    if not video_url:
        return JsonResponse({"error": "Missing video URL"}, status=400)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.xhcdn.com",  # Set to the original source domain
        "Accept": "*/*",
    }

    try:
        response = requests.get(video_url, headers=headers, stream=True, allow_redirects=True)

        if response.status_code == 403:
            logger.error("403 Forbidden: The video source is blocking the request.")
            return JsonResponse({"error": "403 Forbidden: Access denied"}, status=403)

        if response.status_code != 200:
            logger.error(f"Failed to fetch video: {response.status_code}")
            return JsonResponse({"error": f"Failed to fetch video ({response.status_code})"}, status=response.status_code)

        stream_response = StreamingHttpResponse(
            generate_stream(response),
            content_type=response.headers.get('Content-Type', 'video/mp4')
        )

        filename = f"{title[:50]}.mp4".replace("/", "_")
        stream_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        stream_response['Access-Control-Allow-Origin'] = '*'

        return stream_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Streaming error: {str(e)}")
        return JsonResponse({"error": "Server error while streaming video"}, status=500)



@csrf_exempt
def fetch_video_info(request):
    """Fetch video information with improved error handling"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            url = data.get("url")

            if not url:
                return JsonResponse({"error": "No URL provided"}, status=400)

            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "noplaylist": True,
                "quiet": True,
                "ignoreerrors": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return JsonResponse({"error": "Failed to extract video info"}, status=400)

                # Get the best available format
                formats = info.get('formats', [])
                if not formats:
                    return JsonResponse({"error": "No downloadable formats found"}, status=400)

                best_format = next(
                    (f for f in formats if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none'),
                    None
                )

                if not best_format:
                    return JsonResponse({"error": "No suitable video format found"}, status=400)

                video_url = best_format['url']
                title = info.get('title', 'video').replace('/', '-')

                return JsonResponse({"title": title, "video_url": video_url})

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"YT-DLP Error: {str(e)}")
            return JsonResponse({"error": "Video unavailable or restricted"}, status=403)
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            return JsonResponse({"error": "Internal server error"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
