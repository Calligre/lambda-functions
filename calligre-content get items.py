from boto3.dynamodb.conditions import Key
from decimal import Decimal

import boto3
import pprint
import json
import logging as log
dynamo = boto3.resource('dynamodb', region_name="us-west-2").Table("calligre-posts")

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    log.debug("Received event: " + pprint.pformat(event))

    query_string = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    offset = query_string.get("offset")
    postid = path_params.get("id")

    limit = int(query_string.get("limit", 25))
    if limit > 25:
        limit = 25

    proj="#ts,posterid,#txt,media_link,like_count"
    reservedWords = {
        "#ts":"timestamp",
        "#txt": "text"
    }
    if offset is not None:
        log.debug("Searching for offset: %s" % offset)
        r = dynamo.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").gt(Decimal(0)),
            ExclusiveStartKey={
                "posts":"posts",
                "timestamp": Decimal(offset)
            },
        )
    elif postid is not None:
        log.debug("Selecting post id %s" % postid)
        r = dynamo.query(
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").eq(Decimal(postid)),
        )
    else:
        log.debug("Fell through")
        r = dynamo.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reservedWords,
            KeyConditionExpression=Key("posts").eq("posts") & Key("timestamp").gt(Decimal(0)),
        )

    log.debug(r)

    posts = r.get("Items")
    # Build our details
    for item in posts:
        item['id'] = str(item.get("timestamp"))
        item['poster_name'] = "Lookup Name Result"
        item['poster_icon'] = "http://calligre-profilepics.s3-website-us-west-2.amazonaws.com/profilepic-1.jpg"
        item['current_user_likes'] = True

    nextOffset = r.get("LastEvaluatedKey", {}).get("timestamp")
    if nextOffset is not None:
        nextOffset = str(nextOffset)

    response = {
        "posts": posts,
        "count": r.get("Count", 0),
        "nextOffset" : nextOffset
    }
    return {"statusCode": r.get("ResponseMetadata", {}).get("HTTPStatusCode", 500),
        "body": json.dumps(response, default=decimal_default),
        "headers":{}}
