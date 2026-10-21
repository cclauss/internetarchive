#
# The internetarchive module is a Python/CLI interface to Archive.org.
#
# Copyright (C) 2012-2026 Internet Archive
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
internetarchive.auth
~~~~~~~~~~~~~~~~~~~~

This module contains the Archive.org authentication handlers for HTTPX2.

:copyright: (C) 2012-2024 by Internet Archive.
:license: AGPL 3, see LICENSE for more details.
"""

from __future__ import annotations

import httpx2

from internetarchive.exceptions import AuthenticationError


class S3Auth(httpx2.Auth):
    """Authentication handler for IA-S3 requests.

    Attaches ``LOW`` authorization header to requests, which is
    Archive.org's S3-compatible authentication scheme.

    :param access_key: Your IA-S3 access key.
    :param secret_key: Your IA-S3 secret key.

    :raises AuthenticationError: If credentials are missing when called.

    Usage::

        >>> auth = S3Auth('my_access_key', 'my_secret_key')
        >>> response = httpx2.get(url, auth=auth)
    """

    def __init__(self, access_key: str | None = None, secret_key: str | None = None):
        self.access_key = access_key
        self.secret_key = secret_key

    def auth_flow(self, request):
        if not self.access_key:
            if self.secret_key:
                raise AuthenticationError(
                    'No access_key set! Have you run `ia configure`?'
                )
        if not self.secret_key:
            if self.access_key:
                raise AuthenticationError(
                    'No secret_key set! Have you run `ia configure`?'
                )
            else:
                raise AuthenticationError(
                    'No access_key or secret_key set! Have you run `ia configure`?'
                )

        auth_str = f'LOW {self.access_key}:{self.secret_key}'
        request.headers['Authorization'] = auth_str
        yield request


class S3PostAuth(httpx2.Auth):
    """Authentication handler for IA-S3 POST requests (metadata writes).

    Appends credentials to the request body as form parameters rather
    than using the Authorization header. Used for the Metadata Write API.

    :param access_key: Your IA-S3 access key.
    :param secret_key: Your IA-S3 secret key.
    """

    def __init__(self, access_key: str | None = None, secret_key: str | None = None):
        self.access_key = access_key
        self.secret_key = secret_key

    def auth_flow(self, request):
        auth_str = f'&access={self.access_key}&secret={self.secret_key}'
        content = request.read() + auth_str.encode()
        headers = dict(request.headers)
        headers.pop('content-length', None)
        headers['content-type'] = 'application/x-www-form-urlencoded'
        request = httpx2.Request(
            request.method,
            request.url,
            content=content,
            headers=headers,
            extensions=request.extensions,
        )
        yield request
