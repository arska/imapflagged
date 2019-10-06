# IMAP Flagged Items
i[![Build Status](https://travis-ci.com/arska/imapflagged.svg?branch=master)](https://travis-ci.com/arska/imapflagged)

This is a very short web application showing the number of flagged items in an IMAP mailbox. It caches the number for 5 minutes by default to offload the imap server.

## settings in environment variables
* host: hostname of imap-over-ssl server
* username: imap username
* password: imap password
* folder: imap folder to track (default: INBOX)
* cachetime: number of seconds to cache the result (default: 300 = 5 minutes)
