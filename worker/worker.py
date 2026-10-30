import json
import redis
import boto3
import os
import base64
from demucs.api import Separator, save_audio

endpoint = os.getenv("RUSTFS_ENDPOINT", "http://rustfs-svc:9000")
access_key = os.getenv("AWS_ACCESS_KEY_ID", "user")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "userpassword")
queue_bucket_name = os.getenv("RUSTFS_QUEUE_BUCKET", "queue")
output_bucket_name = os.getenv("RUSTFS_OUTPUT_BUCKET", "output")

client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

redisClient = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

separator = Separator(model='htdemucs',repo=None)

while True:
    queueName, message = redisClient.brpop("separation_queue", timeout=0)
    if message:
        job = json.loads(message)
        songhash = job["songhash"]
        bucket = job["bucket"]
        objectKey = job["object_key"]
        model = job["model"]

        # Download the original audio from RustFS
        audioPath = f"{songhash}.mp3"
        client.download_file(bucket, objectKey, audioPath)

        # Perform waveform separation using the specified model
        origin, separatedTracks = separator.separate_audio_file(audioPath)

        # Make a directory for the separated tracks locally
        os.makedirs(songhash, exist_ok=True)

        # Upload separated tracks back to RustFS
        for trackName, trackData in separatedTracks.items():
            trackPath = f"{songhash}/{trackName}.wav"

            save_audio(trackData, trackPath, samplerate=separator.samplerate)

            trackObjectKey = f"{songhash}/{trackName}.wav"
            client.upload_file(trackPath, output_bucket_name, trackObjectKey)

        # Clean up local files
        os.remove(audioPath)
        for trackName, trackData in separatedTracks.items():
            os.remove(f"{songhash}/{trackName}.wav")
        os.rmdir(songhash)