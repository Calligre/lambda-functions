#!/bin/bash
set -e

export DEP_FOLDER="ext-posts-dependencies"
export DEST_FILE="ext-services.zip"
export HANDLER="PostToExternalServices.py"
rm -f ${DEST_FILE}
pep8 ${HANDLER}
pyflakes ${HANDLER}
mkdir -p ${DEP_FOLDER}
cd ${DEP_FOLDER}
if [ ! -d "requests-2.13.0.dist-info" ]; then
    pip install -t . -r ../ext-social-requirements.txt
    find . -name '*.py' -delete
fi

zip -r ../${DEST_FILE} oauthlib requests requests_oauthlib tweepy six.pyc
cd ..
zip -r ${DEST_FILE} ${HANDLER}
#aws s3 cp ${DEST_FILE} "s3://calligre/${DEST_FILE}"
#aws lambda update-function-code --function-name calligre-external-posts --s3-bucket calligre --s3-key "${DEST_FILE}" --publish --region us-west-2
