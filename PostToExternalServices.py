import json
import logging
import os

import boto3
import requests
import tweepy

AUTH0_BASE = "https://calligre.auth0.com"
FB_BASE = "https://graph.facebook.com/v2.7"
S3_BUCKET = "calligre-media"

s3_client = boto3.client('s3')  # pylint: disable=C0103

secrets = {}  # pylint: disable=C0103

log = logging.getLogger()  # pylint: disable=C0103
log.setLevel(logging.DEBUG)


def set_auth0_client_details():
    log.info("Fetching Auth0 client details")
    try:
        response = s3_client.get_object(
            Bucket="calligre-config",
            Key="auth0_token.json",
        )
    except Exception as ex:
        log.error(ex)
        raise ex

    content = response.get("Body").read()
    tokens = json.loads(content)
    if not tokens.get("AUTH0_CLIENT_ID"):
        log.error("Didn't fetch Auth0 client settings!")
    secrets["AUTH0_CLIENT_ID"] = tokens["AUTH0_CLIENT_ID"]
    secrets["AUTH0_CLIENT_SECRET"] = tokens["AUTH0_CLIENT_SECRET"]


def set_auth0_token():
    log.info("Fetching Auth0 token")
    if not (secrets.get("AUTH0_CLIENT_ID") and
            secrets.get("AUTH0_CLIENT_SECRET")):
        set_auth0_client_details()
    payload = {
        "client_id": secrets.get("AUTH0_CLIENT_ID"),
        "client_secret": secrets.get("AUTH0_CLIENT_SECRET"),
        "audience": "%s/api/v2/" % AUTH0_BASE,
        "grant_type": "client_credentials"
    }
    try:
        token = requests.post("%s/oauth/token" % AUTH0_BASE, json=payload).\
            json()
    except Exception as ex:
        log.error(ex)
        raise ex
    secrets["AUTH0_TOKEN"] = token.get("access_token")
    if not secrets["AUTH0_TOKEN"]:
        log.error("Failed to fetch Auth0 Token!")
        log.error(token)
        raise Exception
    log.info("Auth0 token set: %s", secrets["AUTH0_TOKEN"])


def get_auth0_user_tokens(user_id):
    if not secrets.get("AUTH0_TOKEN"):
        set_auth0_token()
    headers = {"Authorization": "Bearer %s" % secrets.get("AUTH0_TOKEN")}
    try:
        return requests.get("%s/api/v2/users/%s" % (AUTH0_BASE, user_id),
                            headers=headers).\
                            json().\
                            get("identities")

    except Exception as ex:
        log.error(ex)
        raise ex


def post_fb_message(user_token, message):
    fb_data = {
        "message": message,
        "access_token": user_token
    }
    requests.post("%s/me/feed" % FB_BASE, data=fb_data)


def post_fb_photo(user_token, message, file_path):
    fb_photo_data = {
        "caption": message,
        "access_token": user_token
    }
    files = {"file": open(file_path, "rb")}
    requests.post("%s/me/photos" % FB_BASE, data=fb_photo_data, files=files)


def set_twitter_client_details():
    log.info("Fetching Twitter client details")
    try:
        response = s3_client.get_object(
            Bucket="calligre-config",
            Key="twitter_token.json",
        )
    except Exception as ex:
        log.error(ex)
        raise ex

    content = response.get("Body").read()
    tokens = json.loads(content)
    if not tokens.get("TWITTER_CLIENT_ID"):
        log.error("Didn't fetch Twitter client settings!")
        raise Exception
    secrets["TWITTER_CLIENT_ID"] = tokens["TWITTER_CLIENT_ID"]
    secrets["TWITTER_CLIENT_SECRET"] = tokens["TWITTER_CLIENT_SECRET"]


def post_tw_message(access_token, access_secret, message, media_path=None):
    # dev ref: https://dev.twitter.com/rest/reference/post/statuses/update
    if not (secrets.get("TWITTER_CLIENT_ID") and
            secrets.get("TWITTER_CLIENT_SECRET")):
        set_twitter_client_details()
    auth = tweepy.OAuthHandler(secrets.get("TWITTER_CLIENT_ID"),
                               secrets.get("TWITTER_CLIENT_SECRET"))
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)

    if media_path:
        status = api.update_with_media(media_path, message)
    else:
        status = api.update_status(message)
    log.debug(status)


def handler(event, _):
    for record in event["Records"]:
        log.debug(record)
        sns = record.get("Sns")
        if not sns:
            continue
        text = sns.get("Message")
        attrs = sns.get("MessageAttributes", {})
        userid = attrs.get("userid", {}).get("Value")
        post_fb = attrs.get("facebook", {}).get("Value", False)
        post_tw = attrs.get("twitter", {}).get("Value", False)

        # parse the fb & Twitter flags, because SNS is only Strings/Ints/Bytes
        if post_fb:
            post_fb = post_fb == "True"
        if post_tw:
            post_tw = post_tw == "True"

        media_s3 = attrs.get("media_s3", {}).get("Value")
        file_path = None
        if media_s3:
            file_path = os.path.join("/tmp", media_s3)
            with open(file_path, "wb") as data:
                s3_client.download_fileobj(S3_BUCKET, media_s3, data)

        for network in get_auth0_user_tokens(userid):
            if network.get("connection") == "facebook" and post_fb:
                access_token = network.get("access_token")
                if media_s3:
                    post_fb_photo(access_token, text, file_path)
                else:
                    post_fb_message(access_token, text)
            elif network.get("connection") == "twitter" and post_tw:
                access_token = network.get("access_token")
                access_secret = network.get("access_token_secret")
                post_tw_message(access_token, access_secret, text, file_path)
