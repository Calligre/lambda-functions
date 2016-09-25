import boto3, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Not, Key, Attr
dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    path_params = event.get("pathParameters") or {}
    postid = path_params.get("id")
    userid = "auth0userid"

    method = event.get("httpMethod")
    if method == "POST":
        update = "ADD likes :like SET like_count = like_count + :1"
        update_cond = Not(Attr("likes").contains(userid))
    elif method == "DELETE":
        update = "DELETE likes :like SET like_count = like_count - :1"
        update_cond = Attr("likes").contains(userid)
    else:
        return {"statusCode": 405}

    if postid is None:
        return {
            "statusCode": 400,
            "body":"Provide a post ID"
        }

    try:
        r = dynamo.update_item(
            Key={
                "posts": "posts",
                "timestamp" : Decimal(postid),
            },
            UpdateExpression=update,
            ExpressionAttributeValues={
                ':like': set([userid]),
                ':1': 1
            },
            ConditionExpression=update_cond
        )
        return {
            "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
        }
    except Exception as e:
        print(e.response)
        if e.response.get("Error") == None:
            return {
                    "statusCode": 500,
                    "body" : "Unknown Error"
                }
        if e.response.get("Error").get("Code") == "ConditionalCheckFailedException":
            return {
                "statusCode": 200,
                "body": "No changes"
            }
        else:
            return {
                "statusCode": 500,
                "body" : "%s: %s" % (e.response.get("Error", {}).get("Code"), e.response.get("Error", {}).get("Message"))
            }


# curl -H "Content-Type: application/json" -v -d '{"userid":12}' -X POST https://calligre.com/api/content/1470003029.5935809612274169921875/likes
