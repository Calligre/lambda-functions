import boto3, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Not, Key, Attr

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    postid = event.get("path", {}).get("id")
    userid = event.get("userid")
    if postid is not None:
        try:
            r = dynamo.update_item(
                Key={
                    "posts": "posts",
                    "timestamp" : Decimal(postid),
                },
                UpdateExpression="ADD likes :like SET like_count = like_count + :1",
                ExpressionAttributeValues={
                    ':like': set([userid]),
                    ':1': 1
                },
                ConditionExpression=Not(Attr("likes").contains(userid))
            )
            return {
                "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500),
                "msg": "OK"
            }
        except Exception as e:
            print(e.response)
            if e.response.get("Error") != None:
                if e.response.get("Error").get("Code") == "ConditionalCheckFailedException":
                    return {
                        "statusCode": 200,
                        "msg" : "Like already exists"
                    }
                else:
                    return {
                        "statusCode": 500,
                        "msg" : "%s: %s" % (e.response.get("Error", {}).get("Code"), e.response.get("Error", {}).get("Message"))
                    }
            else:
                return {
                        "statusCode": 500,
                        "msg" : "Unknown Error"
                    }
    else:
        return {"statusCode": 400}
# curl -H "Content-Type: application/json" -v -d '{"userid":12}' -X POST https://calligre.com/api/content/1470003029.5935809612274169921875/likes
