import json
import decimal

import boto3
from boto3.dynamodb.conditions import Key


REGION = "us-west-2"
DYNAMO = boto3.resource("dynamodb", region_name=REGION).Table("calligre-posts")


def lambda_handler(event, _context):
    path_params = event.get("pathParameters", {})
    postid = path_params.get("id")

    if postid is None:
        return {
            "statusCode": 400,
            "msg": "No post ID provided"
        }

    key_condition = Key("posts").eq("posts") & Key("timestamp").eq(
        decimal.Decimal(postid))
    response = DYNAMO.query(
        ProjectionExpression="likers",
        KeyConditionExpression=key_condition,
    )
    if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500) == 500:
        return {
            "statusCode": 500,
            "msg": "Internal Server Error"
        }

    items = response.get("Items", [])
    if len(items) != 1:
        return {
            "statusCode": 404,
            "body": "No post matching that ID found"
        }

    # TODO: actual lookups
    # liker_ids = items[0].get("likers", [])
    # SQL lookup: select id, name from users where id in liker_ids
    likers = {
        "temp id": "Testing User 1",
        "temp id 2": "Testing User 2",
    }

    return {
        "statusCode": 200,  # or PostgresError
        "body": json.dumps(likers)
    }
