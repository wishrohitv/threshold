AVOID_CHARACTERS = [
    " ",
    "<",
    ">",
    "#",
    "%",
    "{",
    "}",
    "|",
    "\\",
    "^",
    "~",
    "[",
    "]",
    "`",
    '"',
    "'",
    ":",
    ";",
    "/",
    "?",
    "=",
    "&",
    "@",
    "+",
    ".",
    ",",
]


def generate_slug_from_title(post_title):
    cleaned_title = "".join(
        ["-" if char in AVOID_CHARACTERS else char for char in post_title]
    )
    filtered_words = [word for word in cleaned_title.split("-") if word]
    final_url = "-".join(filtered_words)
    return f"{final_url}".lower()
