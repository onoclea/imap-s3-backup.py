# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4
#
# $Id: __new_file__.py 282 2006-08-03 19:37:08Z cn=Sawicki Pawel,ou=People,o=Onoclea $
#
# $License$
#

from boto import s3

# Work around a known Python bug: http://bugs.python.org/issue900744
def get_key_workaround(bucket, key_name):
    s3_max_retry_count      = 100

    for attempt in xrange(s3_max_retry_count):
        try:
            key = bucket.get_key(key_name)
        except ValueError:
            time.sleep(1)
        else:
            break

    if attempt + 1 == s3_max_retry_count:
        raise Exception('Reached maximum S3 retry count %d.' % attempt + 1)

    return key

# EOF
