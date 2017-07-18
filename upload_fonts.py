# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import gzip
import json
import hashlib
import mimetypes
import os
import pprint
import uuid
import StringIO

FONTS_LIST = (
    ('./fonts/noto-fonts/hinted/NotoSansArmenian-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansBengali-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansDevanagari-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansEthiopic-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansGujarati-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansGurmukhi-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansKannada-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansKhmer-Regular.ttf', ['macosx', 'win']),
    ('./fonts/noto-fonts/hinted/NotoSansLao-Regular.ttf', ['macosx', 'win']),
    ('./fonts/noto-fonts/hinted/NotoSansMalayalam-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansMyanmar-Regular.ttf', ['macosx', 'win']),
    ('./fonts/noto-fonts/hinted/NotoSansOriya-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansSinhala-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansTamil-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansTelugu-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansThaana-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/hinted/NotoSansTibetan-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/unhinted/NotoSansCanadianAboriginal-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/unhinted/NotoSansBuginese-Regular.ttf', ['macosx', 'win']),
    ('./fonts/noto-fonts/unhinted/NotoSansCherokee-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/unhinted/NotoSansMongolian-Regular.ttf', ['macosx']),
    ('./fonts/noto-fonts/unhinted/NotoSansYi-Regular.ttf', ['macosx', 'win']),
    ('./fonts/stix-fonts/fonts/STIXMath-Regular.otf', ['macosx'])
)

PLATFORMS = [
    'macosx'
]

FILES_MACOSX = [
    'fonts/noto-fonts/hinted/NotoSansArmenian-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansBengali-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansDevanagari-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansEthiopic-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansGujarati-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansGurmukhi-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansKannada-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansKhmer-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansLao-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansMalayalam-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansMyanmar-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansOriya-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansSinhala-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansTamil-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansTelugu-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansThaana-Regular.ttf',
    'fonts/noto-fonts/hinted/NotoSansTibetan-Regular.ttf',
    'fonts/noto-fonts/unhinted/NotoSansCanadianAboriginal-Regular.ttf',
    'fonts/noto-fonts/unhinted/NotoSansBuginese-Regular.ttf',
    'fonts/noto-fonts/unhinted/NotoSansCherokee-Regular.ttf',
    'fonts/noto-fonts/unhinted/NotoSansMongolian-Regular.ttf',
    'fonts/noto-fonts/unhinted/NotoSansYi-Regular.ttf',
    'fonts/stix-fonts/fonts/STIXMath-Regular.otf'
]

# On some system, the .ttf extension has no associated mimetype.
mimetypes.add_type("application/x-font-ttf", ".ttf")

try:
    import requests
except ImportError:
    raise RuntimeError("requests is required")

def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()

def fetch_records(session, url):
    response = session.get(url)
    response.raise_for_status()
    return response.json()['data']


def files_to_upload(records, files):
    records_by_id = {r['id']: r for r in records if 'attachment' in r}
    to_upload = []
    for filepath, platform in files:
        filename = os.path.basename(filepath)

        identifier = hashlib.md5(filename.encode('utf-8')).hexdigest()
        record_id = str(uuid.UUID(identifier))

        record = records_by_id.pop(record_id, None)
        if record:
            local_hash = sha256(open(filepath, 'rb').read())

            # If file was uploaded gzipped, compare with hash of uncompressed file.
            remote_hash = record.get('attachment').get('original', {}).get('hash')
            if not remote_hash:
                remote_hash = record['attachment']['hash']

            # If hash has changed, upload !
            if local_hash != remote_hash:
                print("File '%s' has changed." % filename)
                to_upload.append((filepath, record))
            else:
                print("File '%s' is up-to-date." % filename)
        else:
            record = {'id': record_id, 'platform': platform}
            to_upload.append((filepath, record))

    # XXX: add option to delete records when files are missing locally
    for id, record in records_by_id.items():
        print("Ignore remote file '%s'." % record['attachment']['filename'])

    return to_upload

def compress_content(content):
    out = StringIO.StringIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(content)
    return out.getvalue()

def create_collection(session, url, force):
    collection = url.split('/')[-1]
    collection_endpoint = '/'.join(url.split('/')[:-1])
    bucket = url.split('/')[-3]
    bucket_endpoint = '/'.join(url.split('/')[:-2])

    resp = session.request('get', bucket_endpoint)
    data = {
        "permissions": {"read": ["system.Everyone"]}
    }

    if resp.status_code == 200:
        existing = resp.json()
        # adding the right permission
        read_perm = existing['permissions'].get('read', [])
        if not "system.Everyone" in read_perm:
            if force:
                session.request('patch', bucket_endpoint, json=data)
            else:
                print('Changing bucket permissions')
    else:
        # creating the bucket
        if force:
            session.request('put', bucket_endpoint, json=data)
        else:
            print('creating bucket')

    if force:
        collection_data = {
            "data": {
                "id": collection
            },
            "permissions": {
                "read": ["system.Everyone"]
            }
        }
        response = session.request('post', collection_endpoint, json=collection_data)
        pprint.pprint(response.json())
        response.raise_for_status()
    else:
        print('adding the collection')

def upload_files(session, url, files, force):
    permissions = {}  # XXX not set yet

    for filepath, record in files:
        mimetype, _ = mimetypes.guess_type(filepath)
        if mimetype is None:
            raise TypeError("Could not recognize the mimetype for %s" % filepath)
        _, filename = os.path.split(filepath)
        filecontent = open(filepath, "rb").read()

        attributes = {
            'platform': record['platform']
        }

        attachment_uri = '%s/%s/attachment?gzipped=true' % (url, record['id'])
        multipart = [("attachment", (filename, filecontent, mimetype))]
        payload = {'data': json.dumps(attributes), 'permissions': json.dumps(permissions)}

        if force:
            response = session.post(attachment_uri, data=payload, files=multipart)
            response.raise_for_status()
            pprint.pprint(response.json())
        else:
            pprint.pprint(payload)

def main():
    parser = argparse.ArgumentParser(description='Upload files to Kinto')
    parser.add_argument('--url', dest='url', action='store', help='Server URL', required=True)
    parser.add_argument('--auth', dest='auth', action='store', help='Credentials', required=True)
    parser.add_argument('--force', dest='force', action='store_true', help='Actually perform actions on the server. Without this no request will be sent')

    args = parser.parse_args()

    if not args.force:
        print('=== DRY RUN === (Use --force to actually perform those actions)')

    session = requests.Session()
    if args.auth:
        session.auth = tuple(args.auth.split(':'))

    url = args.url
    if url.endswith('/'):
        url = url[:-1]

    create_collection(session, url, args.force)

    if not url.endswith('records'):
        url += '/records'

    existing = fetch_records(session, url=url)


    to_upload = files_to_upload(existing, FONTS_LIST)
    upload_files(session, url, to_upload, args.force)

if __name__ == '__main__':
    main()