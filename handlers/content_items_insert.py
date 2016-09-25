# curl -X POST
#      -H "Content-Type: application/json"
#      -d '{"text":"asjdhdjflasjdfas","media_link":"not-a-link-also"}'
#      https://calligre.com/api/content
import decimal
import time
import json

import boto3
from boto3.dynamodb.conditions import Attr


REGION = "us-west-2"
DYNAMO = boto3.resource('dynamodb', region_name=REGION).Table("calligre-posts")


def lambda_handler(event, _context):
    print("Received event: {}".format(event))

    timestamp = decimal.Decimal(time.time())
    body = event.get("body")

    try:
        details = json.loads(body)
    except ValueError:
        return {
            "statusCode": 400,
            "body": "Provide a body please",
        }

    item = {
        "posts": "posts",
        "timestamp": timestamp,
        "poster_id": "temp id",
        "like_count": 0,
        "text": details.get("text", "No text provided"),
    }

    media_link = details.get("media_link")
    if media_link:
        item['media_link'] = media_link

    response = DYNAMO.put_item(
        Item=item,
        ConditionExpression=Attr("timestamp").ne(timestamp)
    )

    code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    return {
        "statusCode": code,
        "body": json.dumps({"id": str(timestamp)}),
    }
