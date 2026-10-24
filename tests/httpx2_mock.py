import re
from contextvars import ContextVar
from functools import wraps

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'

_active_mock = ContextVar('active_httpx2_mock', default=None)


def bind_httpx_mock(mock):
    return _active_mock.set(mock)


def unbind_httpx_mock(token):
    _active_mock.reset(token)


class _QueryMatcher:
    def __init__(self, params, strict_match=True):
        self.params = params
        self.strict_match = strict_match


class _HeaderMatcher:
    def __init__(self, headers):
        self.headers = headers


class _RequestView:
    def __init__(self, request):
        self._request = request

    def __getattr__(self, name):
        return getattr(self._request, name)

    @property
    def url(self):
        return str(self._request.url)

    @property
    def body(self):
        content = self._request.content
        try:
            return content.decode()
        except UnicodeDecodeError:
            return content


class _CallView:
    def __init__(self, request):
        self.request = _RequestView(request)
        self.response = None


class RequestsMock:
    def __init__(self, assert_all_requests_are_fired=True, **kwargs):
        self.assert_all_requests_are_fired = assert_all_requests_are_fired
        self.kwargs = kwargs
        self._mock = None

    def __enter__(self):
        self._mock = _active_mock.get()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def reset(self):
        mock = self._mock or _active_mock.get()
        mock.reset()

    @property
    def calls(self):
        mock = self._mock or _active_mock.get()
        return [_CallView(request) for request in mock.get_requests()]

    def add(
        self,
        method,
        url,
        body=None,
        json=None,
        status=200,
        content_type=None,
        headers=None,
        adding_headers=None,
        **kwargs,
    ):
        matchers = kwargs.pop('match', [])
        del kwargs
        response_headers = dict(headers or {})
        response_headers.update(adding_headers or {})
        if content_type:
            response_headers.setdefault('content-type', content_type)
        options = {
            'url': url,
            'method': method,
            'is_optional': not self.assert_all_requests_are_fired,
        }
        params = {}
        request_headers = {}
        for matcher in matchers:
            if isinstance(matcher, _QueryMatcher):
                if matcher.strict_match:
                    params.update(matcher.params)
            elif isinstance(matcher, _HeaderMatcher):
                request_headers.update(matcher.headers)
        if params:
            options['match_params'] = params
        if request_headers:
            options['match_headers'] = request_headers
        mock = self._mock or _active_mock.get()
        if isinstance(url, str) and '?' not in url and not params:
            options['url'] = re.compile(f'^{re.escape(url.rstrip("/"))}/?(?:\\?.*)?$')
        if isinstance(body, Exception):
            mock.add_exception(body, **options)
        else:
            options['headers'] = response_headers
            if json is not None:
                options['json'] = json
            elif isinstance(body, str):
                options['text'] = body
            elif body is not None:
                options['content'] = body
            mock.add_response(is_reusable=True, status_code=status, **options)


class _ResponsesAPI:
    GET = GET
    POST = POST
    PUT = PUT
    DELETE = DELETE
    RequestsMock = RequestsMock

    class matchers:
        @staticmethod
        def query_param_matcher(params, strict_match=True):
            return _QueryMatcher(params, strict_match)

        @staticmethod
        def header_matcher(headers):
            return _HeaderMatcher(headers)

    @staticmethod
    def add(*args, **kwargs):
        return RequestsMock().add(*args, **kwargs)

    @staticmethod
    def activate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper


responses = _ResponsesAPI()
