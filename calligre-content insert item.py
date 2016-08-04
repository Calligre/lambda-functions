import boto3, time, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    timestamp = Decimal(time.time())
    media_link = event.get("media_link")
    if media_link == "":
        media_link = None
    r = dynamo.put_item(
        Item={
            "posts": "posts",
            "timestamp" : timestamp,
            "posterid" : event.get("poster"),
            # "likes": None, - don't insert likes, ADDing to a NULL results in a type mismatch
            "media_link": media_link,
            "like_count" : 0,
            "text": event.get("text")
        },
        ConditionExpression=Attr("timestamp").ne(timestamp)
    )
    return {
        "id": str(timestamp),
        "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    }

# curl -H "Content-Type: application/json" -v -X POST -d '{"poster":12348,"text":"asjdhdjflasjdfas","media_link":"not-a-link-also"}' https://calligre.com/api/content
