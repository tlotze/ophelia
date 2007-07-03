# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import os.path
import sys
import shutil
import datetime
import pickle

import feedparser

import ophelia.request


def filename(var_dir, key):
    return os.path.join(var_dir, "feeds", key)


def download(key, uri, delta, var_dir):
    fn = filename(var_dir, key)
    now = datetime.datetime.now()
    if os.path.exists(fn):
        try:
            date, doc = pickle.load(open(fn))
        except:
            raise Exception("Can't read feed cache at " + fn)

        if now - date < delta:
            return

    try:
        doc = feedparser.parse(uri)
    except:
        raise Exception("Can't fetch or parse feed at " + uri)

    try:
        pickle.dump((now, doc), open(fn, "w"))
    except:
        raise Exception("Can't write feed cache at " + fn)


class FeedLoader(object):

    def __init__(self, date_format="%c"):
        self.date_format = date_format

    def __call__(self, key, count):
        request = ophelia.request.get_request()
        fn = filename(request.env.var_dir, key)
        try:
            date, doc = pickle.load(open(fn))
            doc.date = date
            doc.formatted_date = ophelia.util.strftime(self.date_format, date)
            del doc.entries[count:]
        except:
            return None
        else:
            return doc
