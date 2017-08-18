# Fonts-ResistFingerprinting
Script for creating and updating the fonts of fingerprinting resistance in Kinto.

## Getting Started
Run following commands to init after you clone this.
```
$ git submodule init
$ git submodule update
```

## How to upload fonts into Kinto Server
```
$ python upload_fonts.py  --url "$SERVICE_URL/buckets/$BUCKET_NAME/collections/$COLLECTION_NAME" --auth user:password --force
```
