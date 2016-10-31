import json
import logging
import os

import boto3
import requests
import tweepy

AUTH0_BASE = "https://calligre.auth0.com"
FB_BASE = "https://graph.facebook.com/v2.7"
S3_BUCKET = "calligre-media"

AUTH0_CLIENT_ID = None
AUTH0_CLIENT_SECRET = None
AUTH0_TOKEN = None

TWITTER_CLIENT_ID = None
TWITTER_CLIENT_SECRET = None

log = logging.getLogger()
log.setLevel(logging.DEBUG)
s3_client = boto3.client('s3')


def setAuth0ClientDetails():
    global AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET
    log.info("Fetching Auth0 client details")
    try:
        response = s3_client.get_object(
            Bucket="calligre-config",
            Key="auth0_token.json",
        )
    except Exception as e:
        log.error(e)
        raise e

    content = response.get("Body").read()
    tokens = json.loads(content)
    if not tokens.get("AUTH0_CLIENT_ID"):
        log.error("Didn't fetch Auth0 client settings!")
    AUTH0_CLIENT_ID = tokens["AUTH0_CLIENT_ID"]
    AUTH0_CLIENT_SECRET = tokens["AUTH0_CLIENT_SECRET"]


def setAuth0Token():
    global AUTH0_TOKEN
    log.info("Fetching Auth0 token")
    if not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET:
        setAuth0ClientDetails()
    payload = {
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": "%s/api/v2/" % AUTH0_BASE,
        "grant_type": "client_credentials"
    }
    try:
        token = requests.post("%s/oauth/token" % AUTH0_BASE, json=payload).\
            json()
    except Exception as e:
        log.error(e)
        raise e
    AUTH0_TOKEN = token.get("access_token")
    if not AUTH0_TOKEN:
        log.error("Failed to fetch Auth0 Token!")
        log.error(token)
        raise Exception
    log.info("Auth0 token set: %s", AUTH0_TOKEN)


def getAuth0UserTokens(user_id):
    if not AUTH0_TOKEN:
        setAuth0Token()
    headers = {"Authorization": "Bearer %s" % AUTH0_TOKEN}
    try:
        return requests.get("%s/api/v2/users/%s" % (AUTH0_BASE, user_id),
                            headers=headers).\
                            json().\
                            get("identities")

    except Exception as e:
        log.error(e)
        raise e


def postFbMessage(user_token, message):
    fb_data = {
        "message": message,
        "access_token": user_token
    }
    requests.post("%s/me/feed" % FB_BASE, data=fb_data)


def postFbPhoto(user_token, message, file_path):
    fb_photo_data = {
        "caption": message,
        "access_token": user_token
    }
    files = {"file": open(file_path, "rb")}
    requests.post("%s/me/photos" % FB_BASE, data=fb_photo_data, files=files)


def setTwitterClientDetails():
    global TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET
    log.info("Fetching Twitter client details")
    try:
        response = s3_client.get_object(
            Bucket="calligre-config",
            Key="twitter_token.json",
        )
    except Exception as e:
        log.error(e)
        raise e

    content = response.get("Body").read()
    tokens = json.loads(content)
    if not tokens.get("TWITTER_CLIENT_ID"):
        log.error("Didn't fetch Twitter client settings!")
        raise Exception
    TWITTER_CLIENT_ID = tokens["TWITTER_CLIENT_ID"]
    TWITTER_CLIENT_SECRET = tokens["TWITTER_CLIENT_SECRET"]


def postTwMessage(access_token, access_secret, message, media_path=None):
    # dev ref: https://dev.twitter.com/rest/reference/post/statuses/update
    if not TWITTER_CLIENT_ID or not TWITTER_CLIENT_SECRET:
        setTwitterClientDetails()
    auth = tweepy.OAuthHandler(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)

    if media_path:
        status = api.update_with_media(media_path, message)
    else:
        status = api.update_status(message)
    log.debug(status)


def postTwPhoto(access_token, access_secret, media_link):
    # get photo from S3
    # post to upload.twitter.com
    # init - https://dev.twitter.com/rest/reference/post/media/upload-init
    # append - https://dev.twitter.com/rest/reference/post/media/upload-append
    # finalize -
    # https://dev.twitter.com/rest/reference/post/media/upload-finalize
    # return media_id
    return None


def handler(event, _):
    for m in event["Records"]:
        log.debug(m)
        sns = m.get("Sns")
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

        for network in getAuth0UserTokens(userid):
            if network.get("connection") == "facebook" and post_fb:
                access_token = network.get("access_token")
                if media_s3:
                    postFbPhoto(access_token, text, file_path)
                else:
                    postFbMessage(access_token, text)
            elif network.get("connection") == "twitter" and post_tw:
                access_token = network.get("access_token")
                access_secret = network.get("access_token_secret")
                postTwMessage(access_token, access_secret, text, file_path)
