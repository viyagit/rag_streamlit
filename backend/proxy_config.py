import requests
from requests_kerberos import HTTPKerberosAuth
from urllib3.util import parse_url
from backend import settings

class HTTPAdapterWithProxyKerberosAuth(requests.adapters.HTTPAdapter):
    def proxy_headers(self, proxy):
        headers = {}
        auth = HTTPKerberosAuth()
        negotiate_details = auth.generate_request_header(
            None,
            parse_url(proxy).host,
            is_preemptive=True
        )
        headers["Proxy-Authorization"] = negotiate_details
        return headers

def get_proxy_session() -> requests.Session:
    """Return a requests session configured with Kerberos proxy auth."""
    session = requests.Session()
    proxy_url = f"http://{settings.PROXY_IP}:{settings.PROXY_PORT}"
    session.proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    session.mount("http://", HTTPAdapterWithProxyKerberosAuth())
    session.mount("https://", HTTPAdapterWithProxyKerberosAuth())
    session.verify = False  # disable SSL verification if proxy intercepts SSL
    return session
