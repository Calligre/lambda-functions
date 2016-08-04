import boto3, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    postid = event.get("path", {}).get("id")
    if postid is not None:
        postid = Decimal(postid)
        r = dynamo.delete_item(
            Key={
                "posts": "posts",
                "timestamp" : postid,
            },
            # stub to check later
            ConditionExpression=Attr("posterid").ne(1),
            ReturnItemCollectionMetrics="SIZE"
        )
        print(r)
        status = r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    else:
        status = 400
    return {"statusCode": status}
# curl -H "Content-Type: application/json" -v -X DELETE https://calligre.com/api/content/1470003029.5935809612274169921875
