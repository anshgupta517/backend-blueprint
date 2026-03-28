"""
Centralised cache key definitions.

All cache keys live here.

Convention: resource:identifier
"""


class UserCacheKeys:
    PREFIX = "user"

    @staticmethod
    def single(user_id: int) -> str:
        """Cache key for a single user by ID."""
        return f"user:{user_id}"

    @staticmethod
    def by_email(email: str) -> str:
        """Cache key for user lookup by email."""
        return f"user:email:{email}"

    @staticmethod
    def list_page(page: int, page_size: int) -> str:
        """Cache key for a paginated user list."""
        return f"user:list:{page}:{page_size}"

    @staticmethod
    def all_pattern() -> str:
        """Pattern to wipe ALL user cache entries at once."""
        return "user:*"


class PostCacheKeys:
    PREFIX = "post"

    @staticmethod
    def single(post_id: int) -> str:
        """Cache key for a single post by ID."""
        return f"post:{post_id}"

    @staticmethod
    def all_pattern() -> str:
        """Pattern to wipe ALL post cache entries at once."""
        return "post:*"
