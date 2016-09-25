# curl -X DELETE
#      -H "Content-Type: application/json"
#      https://calligre.com/api/content/1470003029.5935809612274169921875
import decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key


REGION = "us-west-2"
DYNAMO = boto3.resource("dynamodb", region_name=REGION).Table("calligre-posts")


def lambda_handler(event, _context):
    print("Handling event: {}".format(event))
    path_params = event.get("pathParameters", {})

    postid = path_params.get("id")
    if postid is None:
        return {
            "statusCode": 400,
            "body": "Provide a post ID to delete"
        }

    postid = decimal.Decimal(postid)
    requester_id = "temp id"

    key_condition = Key("posts").eq("posts") & Key("timestamp").eq(postid)
    post = DYNAMO.query(
        ProjectionExpression="poster_id",
        KeyConditionExpression=key_condition,
    ).get("Items")

    if len(post) != 1:
        return {
            "statusCode": 404,
            "body": "The post you are trying to delete doesn't exist.",
        }

    if post[0].get("poster_id") != requester_id:
        return {
            "statusCode": 403,
            "body": "The post you are trying to delete isn't owned by you.",
        }

    response = DYNAMO.delete_item(
        Key={
            "posts": "posts",
            "timestamp": postid,
        },
        # stub to check later
        ConditionExpression=Attr("poster_id").eq(requester_id),
        ReturnItemCollectionMetrics="SIZE"
    )
    print("Got response: {}".format(response))

    code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    return {
        "statusCode": code,
    }
