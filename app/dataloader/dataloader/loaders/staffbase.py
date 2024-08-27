import os
from collections.abc import Generator
from datetime import datetime

import dataloader.loaders.models.staffbase as StaffbaseModels
import requests
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders.base import WebDocumentLoader
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import StaffbaseConfig
from dataloader.loaders.models import WebDocument


class StaffbaseLoader(WebDocumentLoader):
    def __init__(self, config: LoaderConfig):
        self.loader_config = config
        self.config = config._ensure_config(StaffbaseConfig)
        api_key = os.getenv(self.config.api_key_ref)
        if not api_key:
            raise ValueError("API key not found")
        self.client = StaffbaseAPIClient(self.config.url, api_key)

    def lazy_load(self) -> Generator[WebDocument, None, None]:
        posts = self.client.get_posts(
            channels=self.config.channels,
            posts=self.config.posts,
            news_pages=self.config.news_pages,
            publish_filter=self.config.publish_filter,
            language=self.config.language,
        )

        for post in posts:
            content = f"{post['content']['title']} : {post['content']['content']}"
            yield WebDocument(
                metadata=DocumentInfo(name=post["url"], category=self.loader_config.category, roles=self.loader_config.roles),
                content=content,
            )


class StaffbaseAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def _format_post(self, language: str, post: StaffbaseModels.Post, id: str | None = None) -> StaffbaseModels.FormattedPost:
        contents = post.get("contents", {})
        content = None
        if language == "en":
            content = contents.get("en_US", None)
        elif language == "de":
            content = contents.get("de_DE", None)

        if content is None:
            raise Exception(f"Post content not available in {language} for post ID: {post['id']}")

        post_id = id if id is not None else (post.get("id") if post is not None else None)
        if post_id is not None:
            url = self._build_url(post_id)
        else:
            raise Exception("Post ID is required to get post URL")

        formattedPost: StaffbaseModels.FormattedPost = {
            "id": post.get("id"),
            "channelID": post.get("channelID"),
            "externalID": post.get("externalID"),
            "content": content,
            "url": url,
            "campaignId": post.get("campaignId"),
            "planned": post.get("planned"),
            "published": post.get("published"),
            "created": post.get("created"),
            "updated": post.get("updated"),
        }
        return formattedPost

    def _build_url(self, post_id: str) -> str:
        return f"{self.base_url}/content/news/article/{post_id}"

    def _get_posts_by_channel(self, channel_id: str, limit=100, offset=0) -> list[StaffbaseModels.Post]:
        url = f"{self.base_url}/api/channels/{channel_id}/posts"
        headers = {"Authorization": f"Basic {self.api_key}"}
        params = {"limit": limit, "offset": offset}

        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get posts. Status code: {response.status_code}")

        res: StaffbaseModels.ChannelApiResponse = response.json()
        return res.get("data", [])

    def _get_posts_by_news_channel(self, news_page_id: str, limit=100) -> list[StaffbaseModels.Post]:
        initial_url = f"{self.base_url}/api/client/newspages/{news_page_id}/posts"
        headers = {"Authorization": f"Basic {self.api_key}"}
        params = {"limit": limit}

        all_posts = []
        url = initial_url  # Start with the initial URL
        while url:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data: StaffbaseModels.NewsApiResponse = response.json()
            all_posts.extend(data.get("data", []))

            next_link = data.get("links", {}).get("next")
            if not next_link:
                break
            url = next_link.get("href")
            params = {}  # Remove params for the next request

        return all_posts  # Return all fetched posts

    def _get_post_by_id(self, post_id: str):
        url = f"{self.base_url}/api/posts/{post_id}"
        headers = {"Authorization": f"Basic {self.api_key}"}
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get post from url {url}. Status code: {response.status_code}")

        print(f"indexed data from url {url}.")
        return response.json()

    def _get_formatted_channel_posts(
        self, channel_id: str, limit: int, publish_filter: str, language: str
    ) -> list[StaffbaseModels.FormattedPost] | None:
        posts: list[StaffbaseModels.Post] = []
        for offset in range(0, limit, 100):
            res: list[StaffbaseModels.Post] = self._get_posts_by_channel(channel_id, limit=100, offset=offset)
            posts.extend(res)

        filtered_posts = posts

        if publish_filter != "all":
            # Convert publish_filter to a datetime object
            publish_filter_date = datetime.strptime(publish_filter, "%Y-%m-%d")

            filtered_posts: list[StaffbaseModels.Post] = []
            for post in posts:
                update_data = post.get("updated")
                if update_data:
                    if datetime.strptime(update_data[:10], "%Y-%m-%d") >= publish_filter_date:
                        filtered_posts.append(post)
                else:
                    update_data = post.get("created")
                    if update_data:
                        if datetime.strptime(update_data[:10], "%Y-%m-%d") >= publish_filter_date:
                            filtered_posts.append(post)

        formatted_posts: list[StaffbaseModels.FormattedPost] = []
        for post in filtered_posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def _get_formatted_news_pages_posts(
        self, news_pages_ids: list[str], language: str
    ) -> list[StaffbaseModels.FormattedPost] | None:
        posts: list[StaffbaseModels.Post] = []

        for news_page_id in news_pages_ids:
            res: list[StaffbaseModels.Post] = self._get_posts_by_news_channel(news_page_id)
            posts.extend(res)

        formatted_posts: list[StaffbaseModels.FormattedPost] = []
        for post in posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def _get_formatted_posts(self, post_ids: list[str], language: str) -> list[StaffbaseModels.FormattedPost] | None:
        posts: list[StaffbaseModels.Post] = []
        for post_id in post_ids:
            res: StaffbaseModels.Post = self._get_post_by_id(post_id=post_id)
            posts.append(res)

        formatted_posts: list[StaffbaseModels.FormattedPost] = []
        for post in posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def get_posts(
        self,
        channels: list[str],
        posts: list[str],
        news_pages: list[str],
        publish_filter: str,
        language: str,
    ) -> list[StaffbaseModels.FormattedPost]:

        all_posts: list[StaffbaseModels.FormattedPost] = []

        if len(channels) == 0 and len(posts) == 0 and len(news_pages) == 0:
            return all_posts

        if len(channels) > 0:
            for channel in channels:
                channel_posts = self._get_formatted_channel_posts(channel, 100, publish_filter, language)
                if channel_posts is not None:
                    print(f"Found {len(channel_posts)} posts in channel {channel}")
                    all_posts.extend(channel_posts)

        if len(posts) > 0:
            posts_list: list[StaffbaseModels.FormattedPost] | None = self._get_formatted_posts(posts, language)

            if posts_list is not None:
                all_posts.extend(posts_list)

        return all_posts
