#!/bin/bash
set -e

export DEP_FOLDER="ext-posts-dependencies"
mkdir -p ${DEP_FOLDER}
if [ ! -d "${DEP_FOLDER}/requests-2.11.1.dist-info" ]; then
    pip install -t ${DEP_FOLDER} -r requirements.txt
    find ${DEP_FOLDER} -name '*.py' -delete
fi
rm -f ext-services.zip
cd ${DEP_FOLDER}
zip -r ../ext-services.zip oauthlib requests requests_oauthlib tweepy six.pyc
cd ..
zip -r ext-services.zip PostToExternalServices.py
aws s3 cp ext-services.zip "s3://calligre/ext-services.zip"
aws lambda update-function-code --function-name calligre-external-posts --s3-bucket calligre --s3-key "ext-services.zip" --publish --region us-west-2
