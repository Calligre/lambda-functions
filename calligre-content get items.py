from __future__ import print_function
from boto3.dynamodb.conditions import Key
from decimal import Decimal

import boto3
import pprint

def lambda_handler(event, context):
    print("Received event: " + pprint.pformat(event))

    dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")
    limit = event.get("querystring", {}).get("limit", "")
    if len(limit) == 0:
        limit = 25
    else:
        limit = int(limit)
    page = event.get("querystring", {}).get("page")
    postid = event.get("path", {}).get("id")
    proj="#ts,posterid,#txt,media_link,like_count"
    reservedWords = {
        "#ts":"timestamp",
        "#txt": "text"
    }
    if page is not None:
        print("Searching for page: %s" % page)
        r = dynamo.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").gt(Decimal(0)),
            ExclusiveStartKey={
                "posts":"posts",
                "timestamp": Decimal(page)
            },
        )
    elif postid is not None:
        print("Selecting post id %s" % postid)
        r = dynamo.query(
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").eq(Decimal(postid)),
        )
    else:
        print("Fell through")
        r = dynamo.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").gt(Decimal(0)),
        )

    print(r)
    # Lambda truncates Decimal @ ~6 decimal places, we have far more, save everything as a string
    items = r.get("Items")
    for item in items:
        item['timestamp'] = str(item.get("timestamp"))
    nextPage = r.get("LastEvaluatedKey", {}).get("timestamp")
    if nextPage is not None:
        nextPage = str(nextPage)
    res = {
        "items": items,
        "count": r.get("Count", 0),
        "statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500),
        "nextPage" : nextPage
    }
    return res
