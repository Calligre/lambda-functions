import logging
import os
import tempfile

import boto3
import requests
import tweepy

AUTH0_BASE = "https://calligre.auth0.com"
AUTH0_API = "{}/api/v2/".format(AUTH0_BASE)
FB_BASE = "https://graph.facebook.com/v2.7"

s3_client = boto3.client('s3')  # pylint: disable=C0103

log = logging.getLogger(__name__)  # pylint: disable=C0103
log.setLevel(logging.DEBUG)

def get_auth0_token():
    payload = {
        "client_id": os.environ['AUTH0_CLIENT_ID'],
        "client_secret": os.environ['AUTH0_CLIENT_SECRET'],
        "audience": AUTH0_API,
        "grant_type": "client_credentials"
    }
    try:
        token = requests.post("{}/oauth/token".format(AUTH0_BASE),
                              json=payload).\
            json()
    except Exception as ex:
        log.exception(ex)
        raise ex
    if not token.get("access_token"):
        log.error("Failed to fetch Auth0 Token!")
        raise Exception("Failed to fetch Auth0 Token!")
    return token.get("access_token")

# We need to have the Auth0 token, so run it on Lambda startup
AUTH0_TOKEN = get_auth0_token()


def get_auth0_user_tokens(user_id):
    headers = {"Authorization": "Bearer {}".format(AUTH0_TOKEN)}
    try:
        return requests.get("{}users/{}".format(AUTH0_API, user_id),
                            headers=headers).\
                            json().\
                            get("identities")

    except Exception as ex:
        log.exception(ex)
        raise ex


def post_fb_message(user_token, message):
    fb_data = {
        "message": message,
        "access_token": user_token
    }
    requests.post("{}/me/feed".format(FB_BASE), data=fb_data)


def post_fb_photo(user_token, message, link):
    fb_photo_data = {
        "caption": message,
        "access_token": user_token,
        "url": link
    }
    requests.post("{}/me/photos".format(FB_BASE), data=fb_photo_data)


def post_tw_message(access_token, access_secret, message, media):
    auth = tweepy.OAuthHandler(os.environ['TWITTER_CLIENT_ID'],
                               os.environ['TWITTER_CLIENT_SECRET'])
    auth.set_access_token(access_token, access_secret)
    twitter = tweepy.API(auth)

    if media.get('bucket'):
        f = tempfile.mkstemp(prefix=media.get('key'))
        # We want the S3 client to write to it, and the Twitter client to read
        # close the open file descriptor
        f[0].close()
        file_path = f[1]
        s3_client.download_file(media.get('bucket'),
                                media.get('key'),
                                file_path)
        log.debug(twitter.update_with_media(file_path, message))
        os.remove(file_path)
        return

    if media.get('link'):
        if len(message) > 113:
            message = message[0:113] + "..."
        message = '{} {}'.format(message, media.get('link'))

    log.debug(twitter.update_status(message))


def handler(event, _):  # pylint: disable=R0912
    if len(secrets) == 0:
        set_secrets()
    for record in event.get("Records", []):
        log.debug(record)
        sns = record.get("Sns")
        if not sns:
            continue
        text = sns.get("Message")
        attrs = sns.get("MessageAttributes", {})
        userid = attrs.get("userid", {}).get("Value")
        post_fb = attrs.get("facebook", {}).get("Value")
        post_tw = attrs.get("twitter", {}).get("Value")

        # parse the fb & Twitter flags, because SNS is only Strings/Ints/Bytes
        if post_fb:
            post_fb = post_fb == "True"
        if post_tw:
            post_tw = post_tw == "True"

        media_s3_bucket = attrs.get("media_s3_bucket", {}).get("Value")
        media_s3_key = attrs.get("media_s3_key", {}).get("Value")

        # Handle three cases: Media is in our S3 bucket, or is a link, or
        # no media
        # If our media is in our S3 bucket, build a link from that
        if media_s3_bucket and media_s3_key:
            tw_media = {'bucket': media_s3_bucket, 'key': media_s3_key}
            fb_media = '{}/{}/{}'.format(s3_client.meta.endpoint_url,
                                         media_s3_bucket,
                                         media_s3_key)
        elif attrs.get("media_link", {}).get("Value"):
            fb_media = attrs.get("media_link", {}).get("Value")
            tw_media = {'link': fb_media}
        else:
            tw_media = {}
            fb_media = None

        for network in get_auth0_user_tokens(userid):
            if network.get("connection") == "facebook" and post_fb:
                access_token = network.get("access_token")
                # FB API can take a media URL, so pass media_link in
                if fb_media:
                    post_fb_photo(access_token, text, fb_media)
                else:
                    post_fb_message(access_token, text)
            elif network.get("connection") == "twitter" and post_tw:
                access_token = network.get("access_token")
                access_secret = network.get("access_token_secret")
                post_tw_message(access_token, access_secret, text, tw_media)
