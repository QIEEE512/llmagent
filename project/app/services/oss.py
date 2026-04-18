from __future__ import annotations

import base64
import hmac
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from hashlib import sha256
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from urllib.parse import quote

import httpx

from app.config import settings


@dataclass(frozen=True)
class OssPutResult:
    bucket: str
    object_key: str


# Simple in-process cache to avoid re-uploading the same content repeatedly.
# Key: sha256(content) -> object_key
_CONTENT_KEY_CACHE: dict[str, str] = {}


def _require_oss_credentials() -> tuple[str, str]:
    ak = (settings.oss_access_key_id or "").strip()
    sk = (settings.oss_access_key_secret or "").strip()
    if not ak or not sk:
        raise RuntimeError("missing OSS credentials (APP_OSS_ACCESS_KEY_ID/APP_OSS_ACCESS_KEY_SECRET)")
    return ak, sk


def _endpoint_host() -> str:
    # e.g. https://oss-cn-hangzhou.aliyuncs.com -> oss-cn-hangzhou.aliyuncs.com
    ep = (settings.oss_endpoint or "").strip()
    if not ep:
        raise RuntimeError("missing OSS endpoint")
    return ep.replace("https://", "").replace("http://", "").strip("/")


def _gmt_date() -> str:
    # RFC 1123 date
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _guess_content_type(fp: Path) -> str:
    return mimetypes.guess_type(str(fp))[0] or "application/octet-stream"


def _oss_object_key_from_local(fp: Path, *, prefix: str = "uploads/") -> str:
    # keep a simple key, avoid nested paths from user
    name = fp.name.replace("\\", "_")
    return f"{prefix}{name}"


def _sha256_hex(fp: Path) -> str:
    h = sha256()
    with fp.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _authorization(
    *,
    method: str,
    bucket: str,
    object_key: str,
    content_md5: str = "",
    content_type: str = "",
    date: str,
    ak: str,
    sk: str,
    canonicalized_oss_headers: str = "",
    canonicalized_resource: Optional[str] = None,
) -> str:
    # OSS signature v1
    resource = canonicalized_resource or f"/{bucket}/{object_key}"
    string_to_sign = "\n".join(
        [
            method.upper(),
            content_md5,
            content_type,
            date,
            canonicalized_oss_headers + resource,
        ]
    )
    sig = base64.b64encode(hmac.new(sk.encode("utf-8"), string_to_sign.encode("utf-8"), sha1).digest()).decode("utf-8")
    return f"OSS {ak}:{sig}"


def put_file_from_local(fp: Path, *, object_key: Optional[str] = None) -> OssPutResult:
    """Upload a local file to OSS using AccessKey.

    Notes:
    - This keeps dependencies minimal (no aliyun sdk) using OSS REST + signature.
    - For private bucket, caller should use presigned URL for read.
    """

    ak, sk = _require_oss_credentials()
    bucket = settings.oss_bucket
    if not bucket:
        raise RuntimeError("missing OSS bucket")

    fp = Path(fp)
    if not fp.exists() or not fp.is_file():
        raise RuntimeError("local file not found")

    # Content-based cache: same content -> reuse the same object key.
    # This avoids repeated uploads when generating multiple videos from the same image.
    content_hash = _sha256_hex(fp)
    cached_key = _CONTENT_KEY_CACHE.get(content_hash)
    if cached_key:
        return OssPutResult(bucket=bucket, object_key=cached_key)

    object_key = (object_key or _oss_object_key_from_local(fp)).lstrip("/")
    host = f"{bucket}.{_endpoint_host()}"
    date = _gmt_date()
    content_type = _guess_content_type(fp)

    auth = _authorization(
        method="PUT",
        bucket=bucket,
        object_key=object_key,
        content_type=content_type,
        date=date,
        ak=ak,
        sk=sk,
    )

    url = f"https://{host}/{quote(object_key)}"
    headers = {
        "Host": host,
        "Date": date,
        "Content-Type": content_type,
        "Authorization": auth,
    }

    data = fp.read_bytes()
    # Use a short timeout and surface errors.
    with httpx.Client(timeout=30.0) as client:
        r = client.put(url, content=data, headers=headers)
    if r.status_code >= 300:
        raise RuntimeError(f"oss put failed: status={r.status_code} body={r.text[:300]}")

    _CONTENT_KEY_CACHE[content_hash] = object_key

    return OssPutResult(bucket=bucket, object_key=object_key)


def cache_clear() -> None:
    """Clear in-process upload cache (for tests)."""
    _CONTENT_KEY_CACHE.clear()


def presign_get_url(
    *,
    object_key: str,
    expires_in: Optional[int] = None,
    response_content_type: Optional[str] = None,
    response_content_disposition: Optional[str] = None,
) -> str:
    """Generate a signed GET url for a private bucket object.

    Optional response overrides (supported by OSS):
    - response-content-type
    - response-content-disposition
    """

    ak, sk = _require_oss_credentials()
    bucket = settings.oss_bucket
    host = f"{bucket}.{_endpoint_host()}"

    object_key = (object_key or "").lstrip("/")
    if not object_key:
        raise RuntimeError("object_key is required")

    expires = int(expires_in if expires_in is not None else settings.oss_presign_expires_in)
    expires = max(60, expires)

    # Optional response header overrides should be part of the canonicalized resource
    # and therefore included in signature. See OSS doc: subresource params must be signed.
    response_params: dict[str, str] = {}
    if response_content_type:
        response_params["response-content-type"] = response_content_type
    if response_content_disposition:
        response_params["response-content-disposition"] = response_content_disposition

    # Query-string auth uses Expires as unix epoch seconds.
    exp_ts = int(datetime.now(timezone.utc).timestamp()) + expires
    resource = f"/{bucket}/{object_key}"
    canonicalized_resource = resource
    if response_params:
        # Query keys must be sorted lexicographically.
        parts = []
        for k in sorted(response_params.keys()):
            v = response_params[k]
            parts.append(f"{k}={v}")
        canonicalized_resource = canonicalized_resource + "?" + "&".join(parts)

    string_to_sign = "\n".join(["GET", "", "", str(exp_ts), canonicalized_resource])
    sig = base64.b64encode(hmac.new(sk.encode("utf-8"), string_to_sign.encode("utf-8"), sha1).digest()).decode("utf-8")

    # Prefer public base url if provided (e.g. CDN), but signature is still for OSS resource.
    base = (settings.oss_public_base_url or f"https://{host}").rstrip("/")
    params: dict[str, str] = {
        "OSSAccessKeyId": ak,
        "Expires": str(exp_ts),
        "Signature": sig,
    }
    params.update(response_params)

    return f"{base}/{quote(object_key)}?{urlencode(params)}"
