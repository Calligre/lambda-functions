import boto3

ddb = boto3.client('dynamodb', endpoint_url='http://localhost:8000')
ddb.create_table(
    TableName="calligre-posts",
    KeySchema=[
        # This is horrible DynamoDB, but we're only going to be using 1, maybe 2 partitions max
        # With 1|2 partitions, hot partitions aren't much of an issue
        { "AttributeName": "timestamp", "KeyType": "HASH" },
        { "AttributeName": "uuid", "KeyType": "RANGE" }
    ],
    AttributeDefinitions=[
        { "AttributeName": "timestamp", "AttributeType": "N" },
        { "AttributeName": "uuid", "AttributeType": "S" },

    ],
    ProvisionedThroughput={
        "ReadCapacityUnits": 5,
        "WriteCapacityUnits": 5
    }
)
