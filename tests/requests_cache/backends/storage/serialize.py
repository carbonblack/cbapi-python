import base64
import io
import json
import zlib

from requests.structures import CaseInsensitiveDict

from .compat import HTTPResponse, text_type


def _b64_encode_bytes(b):
    return base64.b64encode(b).decode("ascii")


def _b64_encode_str(s):
    return _b64_encode_bytes(s.encode("utf8"))


def _b64_encode(s):
    if isinstance(s, text_type):
        return _b64_encode_str(s)
    return _b64_encode_bytes(s)


def _b64_decode_bytes(b):
    return base64.b64decode(b.encode("ascii"))


def _b64_decode_str(s):
    return _b64_decode_bytes(s).decode("utf8")


class Serializer(object):

    def dumps(self, response, body=None):

        if body is None:
            body = response.read(decode_content=False)

            # NOTE: 99% sure this is dead code. I'm only leaving it
            #       here b/c I don't have a test yet to prove
            #       it. Basically, before using
            #       `cachecontrol.filewrapper.CallbackFileWrapper`,
            #       this made an effort to reset the file handle. The
            #       `CallbackFileWrapper` short circuits this code by
            #       setting the body as the content is consumed, the
            #       result being a `body` argument is *always* passed
            #       into cache_response, and in turn,
            #       `Serializer.dump`.
            response._fp = io.BytesIO(body)

        data = {
            "response": {
                "body": _b64_encode_bytes(body),
                "headers": dict(
                    (_b64_encode(k), _b64_encode(v))
                    for k, v in response.headers.items()
                ),
                "status": response.status,
                "version": response.version,
                "reason": _b64_encode_str(response.reason),
                "strict": response.strict,
                "decode_content": response.decode_content,
            },
        }

        return zlib.compress(
                json.dumps(
                    data, separators=(",", ":"), sort_keys=True,
                ).encode("utf8"),
                )

    def loads(self, data):
        # Short circuit if we've been given an empty set of data
        if not data:
            return

        # Dispatch to the actual load method for the given version
        try:
            return self._loads_v2(data)
        except AttributeError:
            print("attributeerror!!!")
            # This is a version we don't have a loads function for, so we'll
            # just treat it as a miss and return None
            return

    def prepare_response(self, cached):
        """Verify our vary headers match and construct a real urllib3
        HTTPResponse object.
        """
        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        if "*" in cached.get("vary", {}):
            return

        body_raw = cached["response"].pop("body")

        headers = CaseInsensitiveDict(data=cached['response']['headers'])
        if headers.get('transfer-encoding', '') == 'chunked':
            headers.pop('transfer-encoding')

        cached['response']['headers'] = headers

        try:
            body = io.BytesIO(body_raw)
        except TypeError:
            # This can happen if cachecontrol serialized to v1 format (pickle)
            # using Python 2. A Python 2 str(byte string) will be unpickled as
            # a Python 3 str (unicode string), which will cause the above to
            # fail with:
            #
            #     TypeError: 'str' does not support the buffer interface
            body = io.BytesIO(body_raw.encode('utf8'))

        return HTTPResponse(
            body=body,
            preload_content=False,
            **cached["response"]
        )

    def _loads_v2(self, data):
        try:
            cached = json.loads(zlib.decompress(data).decode("utf8"))
        except ValueError:
            return

        # We need to decode the items that we've base64 encoded
        cached["response"]["body"] = _b64_decode_bytes(
            cached["response"]["body"]
        )
        cached["response"]["headers"] = dict(
            (_b64_decode_str(k), _b64_decode_str(v))
            for k, v in cached["response"]["headers"].items()
        )
        cached["response"]["reason"] = _b64_decode_str(
            cached["response"]["reason"],
        )

        return self.prepare_response(cached)