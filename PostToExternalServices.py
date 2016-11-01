import json
import logging
import os

import boto3
import requests
import tweepy

AUTH0_BASE = "https://calligre.auth0.com"
AUTH0_API = "%s/api/v2/" % AUTH0_BASE
FB_BASE = "https://graph.facebook.com/v2.7"
S3_BUCKET = "calligre-media"
S3_CONFIG_BUCKET = "calligre-config"

s3_client = boto3.client('s3')  # pylint: disable=C0103

secrets = {}  # pylint: disable=C0103

log = logging.getLogger()  # pylint: disable=C0103
log.setLevel(logging.DEBUG)


def set_secrets():
    log.info("Fetching secrets from S3")
    try:
        response = s3_client.get_object(
            Bucket=S3_CONFIG_BUCKET,
            Key="secrets.json",
        )
    except Exception as ex:
        log.exception(ex)
        raise ex

    try:
        content = response.get("Body").read()
    except AttributeError as ex:
        log.error("S3 response didn't contain Body: %s", response)
        log.exception(ex)
        raise ex
    retrieved_secrets = json.loads(content)
    assert len(retrieved_secrets) > 0, "Didn't fetch any secrets!"

    if len(retrieved_secrets) < 4:
        log.warning("Number of secrets seems oddly small...")
    secrets.update(retrieved_secrets)


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


def post_fb_photo(user_token, message, file_path):
    fb_photo_data = {
        "caption": message,
        "access_token": user_token
    }
    with open(file_path, "rb") as media_file:
        requests.post("%s/me/photos" % FB_BASE,
                      data=fb_photo_data,
                      files={"file": media_file})


def post_tw_message(access_token, access_secret, message, media_path=None):
    assert (secrets.get("TWITTER_CLIENT_ID") and
            secrets.get("TWITTER_CLIENT_SECRET")),\
            "Twitter Client Tokens not set, failing!"
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

        media_s3 = attrs.get("media_s3", {}).get("Value")
        file_path = None
        if media_s3:
            file_path = os.path.join("/tmp", media_s3)
            s3_client.download_file(S3_BUCKET, media_s3, file_path)

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
