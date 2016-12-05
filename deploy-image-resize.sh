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
if [ ! -d "Pillow-3.4.2.dist-info" ]; then
    # Updates: Use the latest cp27mu-manylinux1 wheel from https://pypi.python.org/pypi/Pillow/
    wget https://pypi.python.org/packages/c0/47/6900d13aa6112610df4c9b34d57f50a96b35308796a3a27458d0c9ac87f7/Pillow-3.4.2-cp27-cp27mu-manylinux1_x86_64.whl
    unzip Pillow-3.4.2-cp27-cp27mu-manylinux1_x86_64.whl
    rm Pillow-3.4.2-cp27-cp27mu-manylinux1_x86_64.whl
fi

zip -r ../${DEST_FILE} PIL
cd ..
zip -r ${DEST_FILE} ${HANDLER}
aws s3 cp ${DEST_FILE} "s3://calligre/${DEST_FILE}"
aws lambda update-function-code --function-name calligre-resize-images --s3-bucket calligre --s3-key "${DEST_FILE}" --publish --region us-west-2
