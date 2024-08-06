from datetime import datetime
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import TypedDict

import requests


class Content(TypedDict):
    content: str
    image: Dict
    teaser: str
    title: str


class Post(TypedDict):
    contents: Dict[str, Content]
    id: Optional[str]
    externalID: Optional[str]
    channelID: Optional[str]
    campaignId: Optional[str]
    planned: Optional[str]
    published: Optional[str]
    created: Optional[str]
    updated: Optional[str]


class ChannelApiResponse(TypedDict):
    total: int
    limit: int
    offset: int
    data: List[Post]


class ApiCursor(TypedDict):
    href: str
    method: str


class NewsApiResponse(TypedDict):
    links: Dict[Literal["next"], ApiCursor]
    data: List[Post]


class FormattedPost(TypedDict):
    content: Content
    url: str
    id: Optional[str]
    externalID: Optional[str]
    channelID: Optional[str]
    campaignId: Optional[str]
    planned: Optional[str]
    published: Optional[str]
    created: Optional[str]
    updated: Optional[str]


class StaffbaseAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def _format_post(self, language: str, post: Post, id: str | None = None) -> FormattedPost:
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

        formattedPost: FormattedPost = {
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

    def _get_posts_by_channel(self, channel_id: str, limit=100, offset=0) -> List[Post]:
        url = f"{self.base_url}/api/channels/{channel_id}/posts"
        headers = {"Authorization": f"Basic {self.api_key}"}
        params = {"limit": limit, "offset": offset}

        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get posts. Status code: {response.status_code}")

        res: ChannelApiResponse = response.json()
        return res.get("data", [])

    def _get_posts_by_news_channel(self, news_page_id: str, limit=100) -> List[Post]:
        initial_url = f"{self.base_url}/api/client/newspages/{news_page_id}/posts"
        headers = {"Authorization": f"Basic {self.api_key}"}
        params = {"limit": limit}

        all_posts = []
        url = initial_url  # Start with the initial URL
        while url:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data: NewsApiResponse = response.json()
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
    ) -> Optional[List[FormattedPost]]:
        posts: List[Post] = []
        for offset in range(0, limit, 100):
            res: List[Post] = self._get_posts_by_channel(channel_id, limit=100, offset=offset)
            posts.extend(res)

        filtered_posts = posts

        if publish_filter != "all":
            # Convert publish_filter to a datetime object
            publish_filter_date = datetime.strptime(publish_filter, "%Y-%m-%d")

            filtered_posts: List[Post] = []
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

        formatted_posts: List[FormattedPost] = []
        for post in filtered_posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def _get_formatted_news_pages_posts(self, news_pages_ids: List[str], language: str) -> Optional[List[FormattedPost]]:
        posts: List[Post] = []

        for news_page_id in news_pages_ids:
            res: List[Post] = self._get_posts_by_news_channel(news_page_id)
            posts.extend(res)

        formatted_posts: List[FormattedPost] = []
        for post in posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def _get_formatted_posts(self, post_ids: List[str], language: str) -> Optional[List[FormattedPost]]:
        posts: List[Post] = []
        for post_id in post_ids:
            res: Post = self._get_post_by_id(post_id=post_id)
            posts.append(res)

        formatted_posts: List[FormattedPost] = []
        for post in posts:
            try:
                formatted_posts.append(self._format_post(language, post))
            except Exception as e:
                print(f"Skipping post ID: {post['id']} because of error {e}")
        return formatted_posts

    def get_posts(
        self, channels: List[str], posts: List[str], news_pages: List[str], publish_filter: str, language: str
    ) -> List[FormattedPost]:

        all_posts: List[FormattedPost] = []

        if len(channels) == 0 and len(posts) == 0 and len(news_pages) == 0:
            return all_posts

        if len(channels) > 0:
            for channel in channels:
                channel_posts = self._get_formatted_channel_posts(channel, 100, publish_filter, language)
                if channel_posts is not None:
                    print(f"Found {len(channel_posts)} posts in channel {channel}")
                    all_posts.extend(channel_posts)

        if len(posts) > 0:
            posts_list: List[FormattedPost] | None = self._get_formatted_posts(posts, language)

            if posts_list is not None:
                all_posts.extend(posts_list)

        return all_posts
