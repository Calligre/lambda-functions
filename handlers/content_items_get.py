import decimal
import json
import logging
import pprint

import boto3
from boto3.dynamodb.conditions import Key


BUCKET = "calligre-profilepics"
REGION = "us-west-2"
PROFILE_PIC = "profilepic-1.jpg"
POST_ICON = "http://{}.s3-website-{}.amazonaws.com/{}".format(
    BUCKET, REGION, PROFILE_PIC)
DYNAMO = boto3.resource("dynamodb", region_name=REGION).Table("calligre-posts")


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def lambda_handler(event, _context):
    logging.debug("Received event: %s", pprint.pformat(event))

    query_string = event.get("queryStringParameters", {})
    path_params = event.get("pathParameters", {})

    offset = query_string.get("offset")
    postid = path_params.get("id")

    limit = int(query_string.get("limit", 25))
    if limit > 25:
        limit = 25

    proj = "#ts,poster_id,#txt,media_link,like_count"
    reserved_words = {
        "#ts": "timestamp",
        "#txt": "text"
    }

    if offset:
        logging.debug("Searching for offset: %s", offset)

        key_condition = Key("posts").eq("posts") & Key("timestamp").gt(
            decimal.Decimal(0))
        response = DYNAMO.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reserved_words,
            KeyConditionExpression=key_condition,
            ExclusiveStartKey={
                "posts": "posts",
                "timestamp": decimal.Decimal(offset)
            },
        )
    elif postid:
        logging.debug("Selecting post id %s", postid)

        key_condition = Key("posts").eq("posts") & Key("timestamp").eq(
            decimal.Decimal(postid))
        response = DYNAMO.query(
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reserved_words,
            KeyConditionExpression=key_condition,
        )
    else:
        logging.debug("Fell through")

        key_condition = Key("posts").eq("posts") & Key("timestamp").gt(
            decimal.Decimal(0))
        response = DYNAMO.query(
            Limit=limit,
            ScanIndexForward=False,
            ProjectionExpression=proj,
            ExpressionAttributeNames=reserved_words,
            KeyConditionExpression=key_condition,
        )

    logging.debug(response)

    posts = response.get("Items")
    # Build our details
    for item in posts:
        item['id'] = str(item.get("timestamp"))
        item['poster_name'] = "Lookup Name Result"
        item['poster_icon'] = POST_ICON
        item['current_user_likes'] = True

    next_offset = response.get("LastEvaluatedKey", {}).get("timestamp", '')

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
    if response.get("Count", 0) == 0:
        status = 404

    body = {
        "posts": posts,
        "count": response.get("Count", 0),
        "nextOffset": next_offset,
    }

    return {
        "statusCode": status,
        "body": json.dumps(body, default=decimal_default),
    }
