import yt_dlp
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

@require_GET
def stream_video(request):
    video_url = request.GET.get("url")
    title = request.GET.get("title", "video")

    if not video_url:
        return JsonResponse({"error": "Missing video URL"}, status=400)

    try:
        response = requests.get(video_url, stream=True)
        
        # Create streaming response with proper headers
        stream_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type', 'video/mp4')
        )
        
        # Set download headers
        filename = f"{title[:50]}.mp4".replace("/", "_")
        stream_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        stream_response['Access-Control-Allow-Origin'] = '*'  # Only for development!
        return stream_response

    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        return JsonResponse({"error": "Download failed"}, status=500)

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
                    return JsonResponse({"error": "Failed to extract video information"}, status=400)

                # Get best available format
                if 'url' in info:
                    video_url = info['url']
                else:
                    formats = info.get('formats', [])
                    if not formats:
                        return JsonResponse({"error": "No downloadable formats found"}, status=400)
                    
                    # Find best MP4 format with audio
                    best_format = next(
                        (f for f in formats 
                         if f.get('ext') == 'mp4' 
                         and f.get('acodec') != 'none'
                         and f.get('vcodec') != 'none'),
                        None
                    )
                    
                    if not best_format:
                        return JsonResponse({"error": "No suitable video format found"}, status=400)
                    
                    video_url = best_format['url']

                title = info.get('title', 'video').replace('/', '-')
                return JsonResponse({"title": title, "video_url": video_url})

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"YT-DLP Error: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({"error": "Video unavailable or restricted"}, status=403)
        except KeyError as e:
            logger.error(f"Key Error: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({"error": "Invalid video data structure"}, status=500)
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({"error": "Internal server error"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)