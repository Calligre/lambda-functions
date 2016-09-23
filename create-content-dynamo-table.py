import boto3

db = boto3.client('dynamodb', endpoint_url='http://localhost:8000')
db.create_table(
    TableName="calligre-posts",
    KeySchema=[
        # This is horrible DynamoDB, but we're only going to be using 1, maybe 2 partitions max
        # With 1|2 partitions, hot partitions aren't much of an issue
        { "AttributeName": "posts", "KeyType": "HASH" },
        { "AttributeName": "timestamp", "KeyType": "RANGE" }
    ],
    AttributeDefinitions=[
        { "AttributeName": "timestamp", "AttributeType": "N" },
        { "AttributeName": "posts", "AttributeType": "S" },

    ],
    ProvisionedThroughput={
        "ReadCapacityUnits": 5,
        "WriteCapacityUnits": 5
    }
)

# db.delete_table(TableName="calligre-posts")
