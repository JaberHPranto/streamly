import subprocess
from pathlib import Path

import boto3
from boto3.compat import os
from settings import Settings

settings = Settings()


class VideoTranscoder:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def download_video(self, output_path: str):
        self.s3_client.download_file(settings.S3_BUCKET, settings.S3_KEY, output_path)

    def transcode_video(self, input_path: str, output_dir: str):
        # ---- HLS ----
        # cmd = [
        #     "ffmpeg",
        #     # video source
        #     "-i",
        #     input_path,
        #     # split single video stream into 3 streams and scale each to 360p, 720p, and 1080p. `fast_bilinear` is a fast scaling algorithm. yuv420p is the output format (converts the video to standard 8-bit yuv420 for high-profile).
        #     "-filter_complex",
        #     "[0:v]split=3[v1][v2][v3];"
        #     "[v1]scale=640:360:flags=fast_bilinear[360p];"
        #     "[v2]scale=1280:720:flags=fast_bilinear[720p];"
        #     "[v3]scale=1920:1080:flags=fast_bilinear[1080p]",
        #     # mapping filtered output stream. output stream 0 = 360p, 1 = 720p, 2 = 1080p.
        #     "-map",
        #     "[360p]",
        #     "-map",
        #     "[720p]",
        #     "-map",
        #     "[1080p]",
        #     # video codec and settings (libx264 - H.264 codec, veryfast preset - fast encoding speed over size, high profile = high quality/better compression, level 4.1)
        #     "-c:v",
        #     "libx264",
        #     "-preset",
        #     "veryfast",
        #     "-profile:v",
        #     "high",
        #     "-level:v",
        #     "4.1",
        #     # Keyframe settings
        #     "-g",
        #     "48",
        #     "-keyint_min",
        #     "48",
        #     "-sc_threshold",
        #     "0",
        #     # Bitrate settings = 360p: 1000k (1 Mbps), 720p: 4000k (4 Mbps), 1080p: 8000k (8 Mbps)
        #     "-b:v:0",
        #     "1000k",
        #     "-b:v:1",
        #     "4000k",
        #     "-b:v:2",
        #     "8000k",
        #     # HLS output settings - output to HLS format, segment duration = 6 seconds, playlist type = Video On Demand (VOD) - finite streams, independent segments (individually decodable), MPEG-TS segments, no playlist size limit (all segments in the playlist)
        #     "-f",
        #     "hls",
        #     "-hls_time",
        #     "6",
        #     "-hls_playlist_type",
        #     "vod",
        #     "-hls_flags",
        #     "independent_segments",
        #     "-hls_segment_type",
        #     "mpegts",
        #     "-hls_list_size",
        #     "0",
        #     "-master_pl_name",
        #     "master.m3u8",
        #     # Stream mapping
        #     "-var_stream_map",
        #     "v:0 v:1 v:2",
        #     "-hls_segment_filename",
        #     # output_dir/
        #     # ├── master.m3u8
        #     # ├── 0/
        #     # │   ├── playlist.m3u8
        #     # │   ├── segment_000.ts
        #     # │   └── segment_001.ts ...
        #     # ├── 1/
        #     # │   └── ...
        #     # └── 2/
        #     #     └── ...
        #     f"{output_dir}/%v/segment_%03d.ts",
        #     f"{output_dir}/%v/playlist.m3u8",
        # ]
        # ---- Dash ----
        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-filter_complex",
            "[0:v]split=3[v1][v2][v3];"
            "[v1]scale=640:360:flags=fast_bilinear,format=yuv420p[360p];"
            "[v2]scale=1280:720:flags=fast_bilinear,format=yuv420p[720p];"
            "[v3]scale=1920:1080:flags=fast_bilinear,format=yuv420p[1080p]",
            # 360p video stream
            "-map",
            "[360p]",
            "-c:v:0",
            "libx264",
            "-b:v:0",
            "1000k",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-g",
            "48",
            "-keyint_min",
            "48",
            # 720p video stream
            "-map",
            "[720p]",
            "-c:v:1",
            "libx264",
            "-b:v:1",
            "4000k",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-g",
            "48",
            "-keyint_min",
            "48",
            # 1080p video stream
            "-map",
            "[1080p]",
            "-c:v:2",
            "libx264",
            "-b:v:2",
            "8000k",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-g",
            "48",
            "-keyint_min",
            "48",
            # Audio stream
            "-map",
            "0:a?",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            # DASH specific settings
            "-use_timeline",
            "1",
            "-use_template",
            "1",
            "-window_size",
            "0",
            "-adaptation_sets",
            "id=0,streams=v id=1,streams=a",
            "-f",
            "dash",
            f"{output_dir}/manifest.mpd",
        ]

        process = subprocess.run(cmd)

        if process.returncode != 0:
            print(f"Transcoding failed: {process.stderr}")
            raise Exception(f"Transcoding failed with return code {process.returncode}")

    def _get_content_type(self, file_path: str) -> str:
        if file_path.endswith(".mpd"):
            return "application/dash+xml"
        elif file_path.endswith(".m4s"):
            return "video/iso.segment"
        elif file_path.endswith(".mp4"):
            return "video/mp4"
        elif file_path.endswith(".ts"):
            return "video/MP2T"
        elif file_path.endswith(".m3u8"):
            return "application/vnd.apple.mpegurl"
        else:
            return "application/octet-stream"

    def upload_video(self, prefix: str, output_dir: str):
        for root, _, files in os.walk(output_dir):
            for file in files:
                local_path = os.path.join(root, file)
                s3_key = f"{prefix}/{os.path.relpath(local_path, output_dir)}"

                self.s3_client.upload_file(
                    local_path,
                    settings.S3_PROCESSED_VIDEOS_BUCKET,
                    s3_key,
                    ExtraArgs={
                        "ACL": "public-read",
                        "ContentType": self._get_content_type(local_path),
                    },
                )

    def process_video(self):
        input_path: Path | None = None
        output_dir: Path | None = None

        try:
            work_dir = Path("/tmp/workspace")
            work_dir.mkdir(exist_ok=True)

            input_path = work_dir / "input.mp4"
            output_dir = work_dir / "output"
            output_dir.mkdir(exist_ok=True)

            self.download_video(str(input_path))
            self.transcode_video(str(input_path), str(output_dir))
            self.upload_video(settings.S3_KEY, str(output_dir))

        finally:
            if input_path is not None and input_path.exists():
                input_path.unlink()

            if output_dir is not None and output_dir.exists():
                import shutil

                shutil.rmtree(output_dir)


VideoTranscoder().process_video()
