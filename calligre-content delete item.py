import boto3, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Attr, Key
dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    path_params = event.get("pathParameters") or {}
    postid = path_params.get("id")

    if postid is None:
        return {"statusCode": 400, "body":"Provide a post ID to delete"}

    postid = Decimal(postid)
    requester_id = "temp id"

    post = dynamo.query(
        ProjectionExpression="poster_id",
        KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").eq(postid),
    ).get("Items")

    if len(post) != 1:
        return {"statusCode": 404, "body": "The post you are trying to delete doesn't exist."}
    if post[0].get("poster_id") != requester_id:
        return {"statusCode": 403, "body": "The post you are trying to delete isn't owned by you."}
    r = dynamo.delete_item(
        Key={
            "posts": "posts",
            "timestamp" : postid,
        },
        # stub to check later
        ConditionExpression=Attr("poster_id").eq(requester_id),
        ReturnItemCollectionMetrics="SIZE"
    )
    print(r)
    return {"statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)}
# curl -H "Content-Type: application/json" -v -X DELETE https://calligre.com/api/content/1470003029.5935809612274169921875
