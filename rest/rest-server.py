
import argparse
from flask import Flask, make_response, request, Response
import json, jsonpickle
import os
import base64



app = Flask(__name__)

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
    data = request.get_json(force=True)


'''
Route /apiv1/queue/[GET] will dump the queued entries from the Redis database
'''
@app.route('/apiv1/queue', methods=['GET'])
def queue():
    data = request.get_json(force=True)


'''
Route /apiv1/track/<string:track> is a GET request that will return the specified track 
as a binary download. The track parameter can be any of base, vocals, drums, or other. 
The response will have the appropriate Content-Type and Content-Disposition headers set 
so that the client can save the file with the correct name and extension.
The track information will be passed in the form of the unique identifier
(songhash) that was returned by the /apiv1/separate route.
'''
@app.route('/apiv1/track/<string:track>', methods=['GET'])
def track(track):
    trackFile = getTrackFile(track)
    response = make_response(trackFile)
    response.headers.set('Content-Type', 'mp3')
    response.headers.set(
        'Content-Disposition', 'attachment', filename='%s.mp3' % track)
    return response


'''
Route /apiv1/remove//track [GET] will remove the corresponding track. 
This could be a DELETE response since that would be a more "restful" semantics.
The track information will be passed in the form of the unique identifier 
(songhash) that was returned by the /apiv1/separate route.
'''
@app.route('/apiv1/remove/<string:track>', methods=['GET'])
def remove(track):
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