import logging
import os
from tempfile import mkstemp
from urllib import unquote_plus

from PIL import Image
import boto3

s3 = boto3.client('s3')  # pylint: disable=C0103

log = logging.getLogger(__name__)  # pylint: disable=C0103
log.setLevel(logging.DEBUG)

DEST_BUCKET = os.environ.get('DEST_BUCKET', 'calligre-images')


def handler(event, _):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        # S3 keys are urlencoded in event notifications
        # https://docs.aws.amazon.com/AmazonS3/latest/dev/notification-content-structure.html
        key = unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']
        log.debug("Got new file: %s:%s, size %d", bucket, key, size)
        original = get_file(bucket, key)
        resized = resize_image(original)
        put_file(resized, DEST_BUCKET, key)
        delete_file(bucket, key)


def get_file(bucket, key):
    log.debug("Fetching file: %s:%s", bucket, key)
    try:
        _, dest = mkstemp()
        s3.download_file(bucket, key, dest)
        return dest
    except Exception as ex:
        log.exception(ex)
        raise ex


def resize_image(src):
    # thumbnail is badly named, it resizes the image, keeping the aspect ratio
    # We use 1024 px on the longest edge as a good balance
    size = (1024, 1024)
    _, outfile = mkstemp()
    try:
        image = Image.open(src)
        log.debug("Resizing: %s, original size: %s", src, image.size())
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
    log.debug("Deleting: %s:%s", bucket, key)
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except Exception as ex:
        log.exception(ex)
        raise ex
