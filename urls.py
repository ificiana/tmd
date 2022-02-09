import re

import requests
from requests.exceptions import MissingSchema

RE_LINK = re.compile(r"\[(.*?)]\((.*?)\)")


def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg")
    try:
        return requests.head(image_url).headers["content-type"] in image_formats
    except MissingSchema:
        pass
    return False


def re_url_helper(_match):
    """
    Helper function for URl parsing and displaying
    """
    _img = is_url_image(_match[1])
    if _img:
        return f"""<figure><img src='{_match[1]}' alt='{_match[2]}'/>
        <figcaption>{_match[2]}</figcaption></figure>""".replace("\n", "")
    return f"<a href='{_match[1]}'>{_match[2] if _match[2] else _match[1]}</a>"
