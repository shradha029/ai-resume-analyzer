"""Text preprocessing shared by training and prediction (it is stored inside the saved pipeline,
so training and inference can never use different cleaning)."""
import re

_TAGS = re.compile(r"<[^>]+>")
_URLS = re.compile(r"https?://\S+|www\.\S+")
_SPACES = re.compile(r"\s+")
TOKEN_PATTERN = r"(?u)\b\w[\w+#.]*\w\b|\b\w\b"   # keeps c++, c#, node.js, scikit-learn style tokens


def clean_text(text) -> str:
    if text is None or (isinstance(text, float) and text != text):
        return ""
    t = _TAGS.sub(" ", str(text))
    t = _URLS.sub(" ", t)
    return _SPACES.sub(" ", t).strip().lower()
