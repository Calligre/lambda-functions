import logging
import os

import boto3
import requests
import tweepy

AUTH0_BASE = "https://calligre.auth0.com"
AUTH0_API = "%s/api/v2/" % AUTH0_BASE
FB_BASE = "https://graph.facebook.com/v2.7"

s3_client = boto3.client('s3')  # pylint: disable=C0103

secrets = {}  # pylint: disable=C0103

log = logging.getLogger(__name__)  # pylint: disable=C0103
log.setLevel(logging.DEBUG)


def set_secrets():
    log.info("Setting secrets from env")
    found = {k: v for k, v in os.environ.iteritems() if
             k.startswith("AUTH0") or k.startswith("TWITTER")}
    assert len(found) > 0, "Didn't fetch any secrets!"
    if len(found) < 4:
        log.warning("Number of secrets seems oddly small...")
    log.info("Identified %s", ", ".join(found.keys()))
    secrets.update(found)


def set_auth0_token():
    log.info("Fetching Auth0 token")
    assert (secrets.get("AUTH0_CLIENT_ID") and
            secrets.get("AUTH0_CLIENT_SECRET")),\
        "Auth0 Client Tokens not set!"

    payload = {
        "client_id": secrets.get("AUTH0_CLIENT_ID"),
        "client_secret": secrets.get("AUTH0_CLIENT_SECRET"),
        "audience": AUTH0_API,
        "grant_type": "client_credentials"
    }
    try:
        token = requests.post("%s/oauth/token" % AUTH0_BASE, json=payload).\
            json()
    except Exception as ex:
        log.exception(ex)
        raise ex
    secrets["AUTH0_TOKEN"] = token.get("access_token")
    assert secrets["AUTH0_TOKEN"], "Failed to fetch Auth0 Token!"
    log.info("Auth0 token set: %s", secrets["AUTH0_TOKEN"])


def get_auth0_user_tokens(user_id):
    if not secrets.get("AUTH0_TOKEN"):
        set_auth0_token()
    headers = {"Authorization": "Bearer %s" % secrets.get("AUTH0_TOKEN")}
    try:
        return requests.get("%susers/%s" % (AUTH0_API, user_id),
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
    requests.post("%s/me/feed" % FB_BASE, data=fb_data)


def post_fb_photo(user_token, message, link):
    fb_photo_data = {
        "caption": message,
        "access_token": user_token,
        "url": link
    }
    requests.post("%s/me/photos" % FB_BASE, data=fb_photo_data)


def post_tw_message(access_token, access_secret, message, media):
    assert (secrets.get("TWITTER_CLIENT_ID") and
            secrets.get("TWITTER_CLIENT_SECRET")),\
            "Twitter Client Tokens not set, failing!"
    auth = tweepy.OAuthHandler(secrets.get("TWITTER_CLIENT_ID"),
                               secrets.get("TWITTER_CLIENT_SECRET"))
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)

    if media.get('bucket'):
        file_path = os.path.join("/tmp", media.get('key'))
        s3_client.download_file(media.get('bucket'),
                                media.get('key'),
                                file_path)
        log.debug(api.update_with_media(file_path, message))
        return

    if media.get('link'):
        if len(message) > 113:
            message = message[0:113]
        message = '{}... {}'.format(message, media.get('link'))

    log.debug(api.update_status(message))


def handler(event, _): # pylint: disable=R0912
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
