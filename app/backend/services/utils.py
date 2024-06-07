from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """is_valid_url checks if the provided URL is a valid URL."""
    try:
        result = urlparse(url)
        components = [result.scheme, result.path]
        if result.netloc != "":
            components.append(result.netloc)
        return all(components)
    except Exception:
        return False
