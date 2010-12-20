#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4
#
# $Id$
#
# $License$
#

import datetime, hashlib, imaplib, logging, sys, time

from boto import s3
from email.parser import Parser as EmailParser, HeaderParser as EmailHeaderParser
from email.message import Message as EmailMessage
from optparse import OptionParser

# Work around a known Python bug: http://bugs.python.org/issue900744
from lib import s3fix

imap_host       = 'imap.gmail.com'
imap_port       = 993
imap_user       = 'username'
imap_pass       = 'password'
#imap_folder     = '[Gmail]/All Mail'
imap_folder     = 'INBOX'

aws_access_key_id       = 'access_key'
aws_secret_access_key   = 'secret_key'

# Must be at most 61 characters long. It is appended with '-s' to store the folder structure.
aws_bucket_prefix       = 'prefix'

aws_bucket_storage      = aws_bucket_prefix
#aws_bucket_structure    = aws_bucket_prefix + '-s'

global options

E_LOGIN_FAILED  = 1
E_SELECT_FAILED = 10

logging.basicConfig()

# Parse options
option_parser = OptionParser()
                                                                
option_parser.add_option('-i', '--init',        dest='init',        action='store_true', help='Force initial synchronization (overwrite everything).',)
#    option_parser.add_option('-f', '--full',        dest='full',        action='store_true', help='Check for any new messages regardles of their seen state.',)
option_parser.add_option('-m', '--check-md5',   dest='check_md5',   action='store_true', help='Check md5 hash sum of every message.',)
#    option_parser.add_option('-u', '--unseen',      dest='unseen',      action='store_true', help='Check only unseen messages (default).', default=True,)
option_parser.add_option('-v', '--verbose',     dest='verbose',     action='store_true', help='Display verbose messages.', )
option_parser.add_option('-r', '--rfc822',      dest='rfc822',      action='store_true', help='Download messages in RFC822 format (default).', default=True,)
option_parser.add_option('-b', '--body',        dest='body',        action='store_true', help='Download raw IMAP body.', )

(options, args) = option_parser.parse_args()

s3_connection = s3.Connection(aws_access_key_id, aws_secret_access_key)
bucket_storage = s3_connection.get_bucket(aws_bucket_storage)
#bucket_structure = s3_connection.get_bucket(aws_bucket_structure)

conn = imaplib.IMAP4_SSL(imap_host, imap_port)

try:
    conn.login(imap_user, imap_pass)
except imaplib.IMAP4.error, e:
    print 'Login failed: %s.' % e
    sys.exit(E_LOGIN_FAILED)

try:
    (type, data) = conn.select(imap_folder, True)

    if type != 'OK':
        raise imaplib.IMAP4.error('Unable to select x %s: %s' % (imap_folder, data))

    if options.verbose: print 'Number of messages found in folder %s: %d' % (imap_folder, int(data[0]))
except imaplib.IMAP4.error, e:
    if options.verbose: print 'Unable to select folder %s: %s.' % (imap_folder, e)
    sys.exit(E_SELECT_FAILED)

(type, data) = conn.uid('SEARCH', None, 'ALL')

if type == 'OK':
    email_header_parser = EmailHeaderParser()
    email = EmailMessage()

    for uid in data[0].split():
        (type, data) = conn.uid('FETCH', uid, r'(RFC822.HEADER)')

        email_headers = email_header_parser.parsestr(data[0][1])

        try:
            message_id = email_headers['message-id']
        except KeyError:
            logging.error('No Message-Id found for message with uid = %d.' % uid)

        sha1 = hashlib.sha1()
        sha1.update(message_id)
        sha1 = sha1.hexdigest()

        logging.debug('Processing message %s.' % message_id)

        if options.body:
            imap_fetch_argument = '(BODY.PEEK[])'
        elif options.rfc822:
            imap_fetch_argument = '(RFC822)'
        else:
            raise Exception('Unknown IMAP fetch argument.')

        (type, data) = (None, None)

        key = s3fix.get_key_workaround(bucket_storage, sha1)

        if key:
            print key.metadata
            if options.init:
                loggin.debug('uploading (forced initial upload).')
            elif options.check_md5:
                (type, data) = conn.uid('FETCH', uid, imap_fetch_argument)
                md5 = hashlib.md5()
                md5.update(data[0][1])
                if md5.hexdigest() == key.etag.strip('"'):
                    print 'md5 sum checks.'
                    continue
                else:
                    print 'md5 sum does not check - uploading.'
            else:
                print 'already uploaded (md5 sum of the message was not checked).'
                continue
        else:
            if options.verbose: print "uploading."

        if not type or not data:
            (type, data) = conn.uid('FETCH', uid, imap_fetch_argument)

        output = bucket_storage.new_key(sha1)
        output.set_contents_from_string(data[0][1])

#        # set/overwrite metadata info
#        key = s3fix.get_key_workaround(bucket_storage, sha1)
#
#        key.set_metadata('X-ImapS3Sync-IMAP-UID', uid)
#        key.set_metadata('X-ImapS3Sync-Uploaded-On', datetime.datetime.now())
#
#        break

try:
    conn.close()
    conn.logout()
except imaplib.IMAP4.error, e:
    print 'Error while closing and logging out: %s' % e

# EOF
