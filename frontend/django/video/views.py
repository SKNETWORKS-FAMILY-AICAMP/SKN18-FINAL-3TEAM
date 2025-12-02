from django.shortcuts import render

def video_page(request, video_id):
    return render(request, "video/index.html", {"video_id": video_id})
