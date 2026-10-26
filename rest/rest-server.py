
import argparse
from flask import Flask, request, Response, send_file
import json, jsonpickle
import os
import base64
import redis

import boto3
from botocore.exceptions import ClientError

endpoint = os.getenv("RUSTFS_ENDPOINT", "http://rustfs:9000")
access_key = os.getenv("AWS_ACCESS_KEY_ID", "user")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "userpassword")
queue_bucket_name = os.getenv("RUSTFS_QUEUE_BUCKET", "queue")
output_bucket_name = os.getenv("RUSTFS_OUTPUT_BUCKET", "output")

s3client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

existing = {item["Name"] for item in s3client.list_buckets().get("Buckets", [])}
if queue_bucket_name not in existing:
    print(f"Creating bucket: {queue_bucket_name}")
    s3client.create_bucket(Bucket=queue_bucket_name)
if output_bucket_name not in existing:
    print(f"Creating bucket: {output_bucket_name}")
    s3client.create_bucket(Bucket=output_bucket_name)

app = Flask(__name__)

redisClient = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
redisListName = 'separation_queue'

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
    data = request.get_json()
    # Hash the audio data to create a unique identifier for the song
    songhash = str(hash(data["mp3"]))
    s3client.put_object(Bucket=queue_bucket_name, Key=songhash + ".mp3", Body=base64.b64decode(data["mp3"]))

    job = {
        "songhash": songhash,
        "bucket": queue_bucket_name,
        "object_key": songhash + ".mp3"
    }

    redisClient.lpush(redisListName, json.dumps(job))

    # Return the songhash in JSON
    response = jsonpickle.encode({'hash':songhash,'reason': "Song enqueued for separation"})
    return Response(
        response=response,
        status=202,
        mimetype='application/json'
    )

'''
Route /apiv1/queue/[GET] will dump the queued entries from the Redis database
'''
@app.route('/apiv1/queue', methods=['GET'])
def queue():
    # Get the items in the redis queue/list
    queueList = redisClient.lrange(redisListName, 0, -1)

    if len(queueList) == 0:
        response = jsonpickle.encode({'queue': 'No items in queue'})
    else:
        # Return the JSON queue list
        response = jsonpickle.encode({'queue': queueList})


    return Response(
        response=response,
        status=200,
        mimetype='application/json'
    )

'''
Route /apiv1/track/<string:songhash>/<string:track> is a GET request that will return the specified track 
as a binary download. The track parameter can be any of bass, vocals, drums, or other. 
The response will have the appropriate Content-Type and Content-Disposition headers set 
so that the client can save the file with the correct name and extension.
The track information will be passed in the form of the unique identifier
(songhash) that was returned by the /apiv1/separate route.
'''
trackTypes = ["bass", "vocals", "drums", "other"]
@app.route('/apiv1/track/<string:songhash>/<string:track>', methods=['GET'])
def getTrack(songhash, track):
    # Check if track type is acceptable
    if track not in trackTypes:
        response = jsonpickle.encode({'message': "Unknown track identifier requested"})
        return Response(
            response=response,
            status=404,
            mimetype='application/json'
        )

    trackObjectKey = f"{songhash}/{track}.wav"
    # Make a directory for the track to load into
    os.makedirs(f'{songhash}/', exist_ok=True)
    
    s3client.download_file(Bucket=output_bucket_name,Key=trackObjectKey,Filename=trackObjectKey)

    return send_file(
        trackObjectKey,
        mimetype='audio/wav',
        as_attachment=True,
        download_name=f'{track}.wav'
    )

def s3_object_exists(bucket_name, object_key):
    try:
        s3client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') in ('404', 'NoSuchKey'):
            return False
        raise
'''
Route /apiv1/remove/hash/track [GET] will remove the corresponding track. 
This could be a DELETE response since that would be a more "restful" semantics.
The track information will be passed in the form of the unique identifier 
(songhash) that was returned by the /apiv1/separate route.
'''
@app.route('/apiv1/remove/<string:songhash>/<string:track>', methods=['DELETE'])
def remove(songhash, track):
    if track not in trackTypes:
        response = jsonpickle.encode({'message': "Unknown track identifier requested"})
        return Response(
            response=response,
            status=400,
            mimetype='application/json'
        )
    trackObjectKey = f"{songhash}/{track}.wav"

    # s3_object_exists will return True if the track exists
    if (s3_object_exists(output_bucket_name,trackObjectKey)):
        try:
            s3client.delete_object(
                Bucket=output_bucket_name,
                Key=trackObjectKey
            )
            response = jsonpickle.encode({'message': f'{trackObjectKey} deleted successfully'})
            return Response(
                response,
                status=200,
                mimetype='application/json'
            )
        except ClientError as e:
            response = jsonpickle.encode({'message': f'Failed to delete {trackObjectKey}: {e}'})
            return Response(
                response,
                status=500,
                mimetype='application/json'
            )
    else:
        response = jsonpickle.encode({'message': f'{trackObjectKey} does not exist'})
        return Response(
            response,
            status=404,
            mimetype='application/json'
        )


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