import json
import random
import string

import boto3


CLIENT = boto3.client('s3')


def lambda_handler(_event, _context):
    # TODO: consider adding x-amz-meta-author w/ principal ID from authorizer
    post = CLIENT.generate_presigned_post(
        Bucket='calligre-images-pending-resize',
        Key=''.join(random.choice(string.ascii_uppercase + string.digits)
                    for _ in range(12))
    )

    return {
        "statusCode": 200,
        "body": json.dumps(post),
        "headers": {},
    }
