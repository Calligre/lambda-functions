from __future__ import print_function

import boto3
import json
import random
import string

s3 = boto3.client('s3')
def lambda_handler(event, context):
    post = s3.generate_presigned_post(
        Bucket='calligre-images-pending-resize',
        Key=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    )
    # Consider adding x-amz-meta-author w/ principal ID from authorizer

    return {"statusCode": 200, "body": json.dumps(post), "headers":{}}
