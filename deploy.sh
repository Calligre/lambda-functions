#!/bin/bash
set -e

if [ ! -d "requests-2.11.1.dist-info" ]; then
    pip install -t . -r requirements.txt
fi
rm -f ext-services.zip
# Would be nice to exclude all the .py files in favour of the .pyc files
zip -r ext-services.zip oauthlib requests requests_oauthlib tweepy six.pyc PostToExternalServices.py
aws s3 cp ext-services.zip "s3://calligre/ext-services.zip"
aws lambda update-function-code --function-name calligre-external-posts --s3-bucket calligre --s3-key "ext-services.zip" --publish --region us-west-2
