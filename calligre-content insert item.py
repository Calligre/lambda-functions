import boto3, time, pprint
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    timestamp = Decimal(time.time())
    details = event.get("body-json", {})
    item = {
        "posts": "posts",
        "timestamp" : timestamp,
        "poster_id" : details.get("poster_id"),
        "like_count" : 0,
        "text": details.get("text", "No text provided")
    }
    media_link = details.get("media_link")
    if media_link:
        item['media_link'] = media_link
    print(r)
    r = dynamo.put_item(
        Item=item,
        ConditionExpression=Attr("timestamp").ne(timestamp)
    )
    return {
        "id": str(timestamp),
        "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    }

# curl -H "Content-Type: application/json" -v -X POST -d '{"poster":12348,"text":"asjdhdjflasjdfas","media_link":"not-a-link-also"}' https://calligre.com/api/content
