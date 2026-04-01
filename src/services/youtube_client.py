"""YouTube Data API v3 ラッパー"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from googleapiclient.discovery import build

from src.config import get_env, get_settings

logger = logging.getLogger(__name__)


class YouTubeTrendClient:
    """YouTubeトレンド動画からキーワードを抽出"""

    def __init__(self) -> None:
        api_key = get_env("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY が設定されていません")
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.region_code = get_settings().trend_sources.youtube.region_code

    def get_trending_keywords(self, max_results: int = 50) -> list[str]:
        """トレンド動画のタイトルからキーワードを抽出"""
        try:
            response = (
                self.youtube.videos()
                .list(
                    part="snippet",
                    chart="mostPopular",
                    regionCode=self.region_code,
                    maxResults=max_results,
                )
                .execute()
            )

            keywords = []
            for item in response.get("items", []):
                title = item["snippet"]["title"]
                # タイトルからキーワード抽出（記号除去、短い単語除外）
                words = re.split(r"[\s\u3000【】「」『』\[\]()（）|｜/／]+", title)
                for word in words:
                    word = word.strip()
                    if len(word) >= 2 and not re.match(r"^[\d\W]+$", word):
                        keywords.append(word)

            # 重複除去しつつ順序保持
            seen = set()
            unique = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique.append(kw)

            logger.info("YouTube: %d件のキーワード抽出", len(unique))
            return unique
        except Exception as e:
            logger.error("YouTube API エラー: %s", e)
            return []


class YouTubeUploader:
    """YouTube動画アップロード"""

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self) -> None:
        settings = get_settings()
        self.credentials_path = Path(settings.youtube.credentials_path)
        self.default_privacy = settings.youtube.default_privacy
        self.default_category = settings.youtube.default_category
        self._service = None

    def _get_authenticated_service(self):
        """OAuth 2.0認証済みのYouTubeサービスを取得"""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        token_path = self.credentials_path.parent / "youtube_token.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"OAuth認証ファイルが見つかりません: {self.credentials_path}\n"
                        "Google Cloud ConsoleからOAuth 2.0クライアントIDをダウンロードしてください。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    @property
    def service(self):
        if self._service is None:
            self._service = self._get_authenticated_service()
        return self._service

    def upload(self, video_path: str, metadata: dict) -> tuple[str, str]:
        """動画をYouTube Shortsにアップロード

        Returns:
            (video_id, video_url)
        """
        from googleapiclient.http import MediaFileUpload

        body = {
            "snippet": {
                "title": metadata.get("title", "Untitled"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": self.default_category,
            },
            "status": {
                "privacyStatus": self.default_privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=256 * 1024,  # 256KB chunks
        )

        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info("アップロード進捗: %d%%", int(status.progress() * 100))

        video_id = response["id"]
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        logger.info("アップロード完了: %s", video_url)
        return video_id, video_url
