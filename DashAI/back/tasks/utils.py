import filetype


def get_bytes_with_type_filetype(data: bytes) -> tuple[bytes, str]:
    """Uses filetype library for lightweight detection."""
    kind = filetype.guess(data)

    if kind is None:
        # Try to detect text
        try:
            data.decode("utf-8")
            return (data, "text")
        except UnicodeDecodeError:
            return (data, "unknown")

    # filetype provides mime type
    mime = kind.mime
    if mime.startswith("image/"):
        return (data, "image")
    elif mime.startswith("audio/"):
        return (data, "audio")
    elif mime.startswith("video/"):
        return (data, "video")
    elif mime == "application/pdf":
        return (data, "pdf")
    elif mime in [
        "application/zip",
        "application/x-rar",
        "application/x-7z-compressed",
    ]:
        return (data, "archive")
    else:
        return (data, "unknown")
