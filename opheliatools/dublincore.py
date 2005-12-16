import datetime

from ophelia import oapi


def bumpDate(*args):
    date = datetime.datetime(*args)
    context = oapi.getContext()
    if hasattr(context, "dc_date"):
        max_date = max(context.dc_date, date)
    else:
        max_date = date
    context.dc_date = max_date
    return max_date
