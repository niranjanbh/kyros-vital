from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_or_ip(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None:
        return str(user.id)
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip, default_limits=["60/minute"])
