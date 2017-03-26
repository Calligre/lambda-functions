import logging
import os
from tempfile import mkstemp
from urllib import unquote_plus

from PIL import Image
import boto3

s3 = boto3.resource('s3')  # pylint: disable=C0103

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
        s3_file_ref = s3.Object(bucket, key)
        original = get_file(s3_file_ref)
        resized = resize_image(original)
        s3_resized_ref = s3.Object(DEST_BUCKET, key)
        put_file(resized, s3_resized_ref)
        delete_file(s3_file_ref)


def get_file(s3_ref):
    log.debug("Fetching file: %s:%s", s3_ref.bucket_name, s3_ref.key)
    try:
        _, dest = mkstemp()
        s3_ref.download_file(dest)
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
        log.debug("Resizing: %s, original size: %dx%d",
                  src,
                  image.width,
                  image.height)
        image.thumbnail(size)
        image.save(outfile, "JPEG")
        return outfile
    except IOError as ex:
        log.exception("Cannot resize image")
        raise ex


def put_file(src, s3_ref):
    log.debug("Putting %s into %s:%s", src, s3_ref.bucket_name, s3_ref.key)
    try:
        with open(src, 'rb') as src_file:
            s3_ref.put(ACL='public-read',
                       Body=src_file,
                       CacheControl="max-age=2419200",
                       ContentType="image/jpeg")
    except Exception as ex:
        log.exception(ex)
        raise ex


def delete_file(s3_ref):
    log.debug("Deleting: %s:%s", s3_ref.bucket_name, s3_ref.key)
    try:
        s3_ref.delete()
    except Exception as ex:
        log.exception(ex)
        raise ex
