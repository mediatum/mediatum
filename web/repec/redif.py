from collections import OrderedDict


def _redif_encode(data):
    redif_result = []

    # sort data by key name, if not already sorted
    if not isinstance(data, OrderedDict):
        data = OrderedDict(sorted(data.items(), key=lambda i: i[0]))

    for key, value in data.items():
        # skip None and False values but not empty strings
        if value in (None, False, ):
            continue

        # repeat ReDIF key for lists
        elif isinstance(value, (list, set, tuple, )):
            for v in value:
                redif_result.append("%s: %s" % (key, _redif_encode_text(v)))

        # treat dicts as sub-templates
        elif isinstance(value, (dict, )):
            cluster = _redif_encode(value)
            if cluster:
                redif_result.append(cluster)

        # treat any other value as text
        else:
            redif_result.append("%s: %s" % (key, _redif_encode_text(value)))

    return "\n".join(redif_result)


def _redif_encode_text(value):
    if isinstance(value, unicode):
        value = value.encode("utf8")
    else:
        value = str(value)

    value = value.replace("\r", "")
    value = value.replace("\n", " ")

    value_tokens = value.split(" ")
    value_lines = [
        ""
    ]

    for value_token in value_tokens:
        value_token = value_token.strip()
        if not value_token:
            continue

        value_lines_last = value_lines[-1]
        if len(value_lines_last) > 120:
            value_lines.append("")
            value_lines_last = value_lines[-1]

        value_lines_last = " ".join((value_lines_last, value_token))
        value_lines[-1] = value_lines_last

    return "\n ".join([l.strip() for l in value_lines])


def redif_encode_archive(data):
    return "\n".join((
        "Template-Type: ReDIF-Archive 1.0",
        _redif_encode(data)
    ))


def redif_encode_series(data):
    return "\n".join((
        "Template-Type: ReDIF-Series 1.0",
        _redif_encode(data)
    ))


def redif_encode_paper(data):
    return "\n".join((
        "Template-Type: ReDIF-Paper 1.0",
        _redif_encode(data)
    ))


def redif_encode_article(data):
    return "\n".join((
        "Template-Type: ReDIF-Article 1.0",
        _redif_encode(data)
    ))


def redif_encode_book(data):
    return "\n".join((
        "Template-Type: ReDIF-Book 1.0",
        _redif_encode(data)
    ))
