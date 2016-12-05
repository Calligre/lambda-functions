import logging
import os
from tempfile import mkstemp
from urllib import unquote_plus

from PIL import Image
import boto3

s3 = boto3.client('s3')  # pylint: disable=C0103

log = logging.getLogger(__name__)  # pylint: disable=C0103
log.setLevel(logging.DEBUG)


def handler(event, _):
    for record in event['Records']:
        _, original = mkstemp()
        bucket = record['s3']['bucket']['name']
        # S3 keys are urlencoded in event notifications
        # https://docs.aws.amazon.com/AmazonS3/latest/dev/notification-content-structure.html
        key = unquote_plus(record['s3']['object']['key'])
        log.debug("Got new file: %s:%s", bucket, key)
        get_file(original, bucket, key)
        resized = resize_image(original)
        put_file(resized,
                 os.environ.get('DEST_BUCKET', 'calligre-images'),
                 key)
        delete_file(bucket, key)


def get_file(dest, bucket, key):
    try:
        log.debug("Fetching file: %s:%s", bucket, key)
        s3.download_file(bucket, key, dest)
    except Exception as ex:
        log.exception(ex)
        raise ex


def resize_image(src):
    size = (1024, 1024)
    _, outfile = mkstemp()
    try:
        log.debug("Resizing: %s", src)
        image = Image.open(src)
        image.thumbnail(size)
        image.save(outfile, "JPEG")
        return outfile
    except IOError as ex:
        log.exception("Cannot resize image")
        raise ex


def put_file(src, bucket, key):
    log.debug("Putting %s into %s:%s", src, bucket, key)
    try:
        s3.upload_file(src, bucket, key)
    except Exception as ex:
        log.exception(ex)
        raise ex


def delete_file(bucket, key):
    try:
        log.debug("Deleting: %s:%s", bucket, key)
        s3.delete_object(Bucket=bucket, Key=key)
    except Exception as ex:
        log.exception(ex)
        raise ex
