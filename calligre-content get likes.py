import boto3, pprint
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Attr, Key
dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")

def lambda_handler(event, context):
    path_params = event.get("pathParameters") or {}
    postid = path_params.get("id")

    if postid is None:
        return {"statusCode": 400, "msg": "No post ID provided"}
    r = dynamo.query(
        ProjectionExpression="likers",
        KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").eq(Decimal(postid)),
    )
    if r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500) == 500:
        return {"statusCode": 500, "msg": "Internal Server Error"}
    items = r.get("Items", [])
    if len(items) != 1:
        return {
            "statusCode": 404,
            "body": "No post matching that ID found"
        }
    liker_ids = items[0].get("likers", [])
    # SQL lookup: select id, name from users where id in liker_ids
    likers = {
        "temp id": "Testing User 1",
        "temp id 2": "Testing User 2"
    }

    return {
        "statusCode": 200, # or PostgresError
        "body": json.dumps(likers)
    }
