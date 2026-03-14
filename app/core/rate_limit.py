from slowapi import Limiter
from slowapi.util import get_remote_address

# get_remote_address extracts the client's IP from the request
# This is the "key" — rate limits are per IP address
limiter = Limiter(key_func=get_remote_address)