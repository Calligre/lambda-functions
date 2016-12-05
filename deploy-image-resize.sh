#!/bin/bash
set -e

export DEP_FOLDER="resize-dependencies"
export DEST_FILE="resize.zip"
export HANDLER="ResizeImage.py"
rm -f ${DEST_FILE}
pep8 ${HANDLER}
pyflakes ${HANDLER}
mkdir -p ${DEP_FOLDER}
cd ${DEP_FOLDER}
if [ ! -d "Pillow-3.1.1-py2.7.egg-info" ]; then
    wget https://raw.githubusercontent.com/Miserlou/lambda-packages/cc02ac84589e92e28c55f811292cdaeae7a87e5d/lambda_packages/Pillow/Pillow-3.1.1.tar.gz
    tar -xzf Pillow-3.1.1.tar.gz
    rm Pillow-3.1.1.tar.gz
    find . -name '*.py' -delete
fi

zip -r ../${DEST_FILE} PIL lib*
cd ..
zip -r ${DEST_FILE} ${HANDLER}
aws s3 cp ${DEST_FILE} "s3://calligre/${DEST_FILE}"
aws lambda update-function-code --function-name calligre-resize-images --s3-bucket calligre --s3-key "${DEST_FILE}" --publish --region us-west-2
