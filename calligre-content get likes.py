import boto3, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Attr, Key

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    proj="likes"

    postid = event.get("path", {}).get("id")
    if postid is None:
        return {"statusCode": 400, "msg": "No post ID specified"}
    r = dynamo.query(
        ScanIndexForward=False,
        ProjectionExpression=proj,
        KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").eq(Decimal(postid)),
    )
    items = r.get("Items", [])
    if len(items) == 0:
        return {
            "statusCode": 404,
            "msg": "No post matching that ID found"
        }
    likes = items[0].get("likes", [])
    print(r)
    return {
        "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500),
        "likers": list(likes)
    }
