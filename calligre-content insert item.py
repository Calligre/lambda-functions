import boto3, time, pprint
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))
    timestamp = Decimal(time.time())
    body = event.get("body")
    try:
        details = json.loads(body)
    except:
        return {"statusCode": 400, "body": "Provide a body please"}
    item = {
        "posts": "posts",
        "timestamp" : timestamp,
        "poster_id" : "temp id",
        "like_count" : 0,
        "text": details.get("text", "No text provided")
    }

    media_link = details.get("media_link")
    if media_link:
        item['media_link'] = media_link

    r = dynamo.put_item(
        Item=item,
        ConditionExpression=Attr("timestamp").ne(timestamp)
    )
    response = {"id": str(timestamp)}

    return {
        "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500),
        "body":json.dumps(response)
    }

# curl -H "Content-Type: application/json" -v -X POST -d '{"text":"asjdhdjflasjdfas","media_link":"not-a-link-also"}' https://calligre.com/api/content
