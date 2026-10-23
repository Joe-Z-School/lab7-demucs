
import argparse
from flask import Flask, make_response, request, Response
import json, jsonpickle
import os
import base64
import redis

import boto3

endpoint = os.getenv("RUSTFS_ENDPOINT", "http://rustfs:9000")
access_key = os.getenv("AWS_ACCESS_KEY_ID", "user")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "userpassword")
bucket_name = os.getenv("RUSTFS_BUCKET", "demucs")

client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

existing = {item["Name"] for item in client.list_buckets().get("Buckets", [])}
if bucket_name not in existing:
    print(f"Creating bucket: {bucket_name}")
    client.create_bucket(Bucket=bucket_name)

app = Flask(__name__)

redisClient = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

@app.route('/')
def index():
    return "Demucs REST server is running."

'''
Route /apiv1/separate[POST] will analyze the JSON base64 encoded data mp3 with 
model 'model' and queue the work for waveform separation. When the analysis is completed 
the specified callback may be called but does not need to succeed. The REST server should 
return a unique identifier (songhash) that can later be used to retrieve the separated tracks or delete them.
'''
@app.route('/apiv1/separate', methods=['POST'])
def separate():
    # Parse and validate the JSON request.
    # Decode the base64-encoded MP3 data.
    # Store the original audio in RustFS.
    # Generate a unique song identifier.
    # Enqueue a job in Redis with the identifier and storage location.
    # Return the identifier to the client.
    data = request.get_json(force=True)
    # Hash the audio data to create a unique identifier for the song
    songhash = str(hash(data["audio"]))
    client.put_object(Bucket=bucket_name, Key=songhash + ".mp3", Body=base64.b64decode(data["audio"]))

    job = {
        "songhash": songhash,
        "bucket": bucket_name,
        "object_key": songhash + ".mp3",
        "model": "htdemucs"
    }

    redisClient.lpush("separation_queue", json.dumps(job))

    return json.dumps({"songhash": songhash})

'''
Route /apiv1/queue/[GET] will dump the queued entries from the Redis database
'''
@app.route('/apiv1/queue', methods=['GET'])
def queue():
    data = request.get_json(force=True)


'''
Route /apiv1/track/<string:track> is a GET request that will return the specified track 
as a binary download. The track parameter can be any of bass, vocals, drums, or other. 
The response will have the appropriate Content-Type and Content-Disposition headers set 
so that the client can save the file with the correct name and extension.
The track information will be passed in the form of the unique identifier
(songhash) that was returned by the /apiv1/separate route.
'''
trackTypes = ["bass", "vocals", "drums", "other"]
@app.route('/apiv1/track/<string:songhash>/<string:track>', methods=['GET'])
def getTrack(songhash, track):
    pass


'''
Route /apiv1/remove//track [GET] will remove the corresponding track. 
This could be a DELETE response since that would be a more "restful" semantics.
The track information will be passed in the form of the unique identifier 
(songhash) that was returned by the /apiv1/separate route.
'''
@app.route('/apiv1/remove/<string:songhash>/<string:track>', methods=['GET'])
def remove(songhash, track):
    pass


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Flask REST server'
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5000,
        help='Port on which to run the server (default: 5000)'
    )

    args = parser.parse_args()

    # Start Flask app
    app.run(host='0.0.0.0', port=args.port)


'''
Helpful commands for Docker:

When creating the image and container for the flask server
    docker build -t rest-server .

To run the flask server in a container
    docker run -p 5000:5000 rest-server

To remove the contianer
    docker rm <container_id>

To remove the image
    docker rmi rest-server

To list the containers
    docker ps -a

To list the images
    docker images

'''