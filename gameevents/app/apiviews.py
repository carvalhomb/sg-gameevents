'''
Defines the methods/endpoints (the views) of the gameevents service.
This defines the interaction points, but the actual logic is treated
by the :mod:`controller`.
'''
from flask import render_template, flash, redirect
from flask import Flask, jsonify, request, abort
from flask import current_app, Blueprint, render_template
from flask.ext.api import status 
from flask.helpers import make_response
from app import app, auth
import datetime
import json
import time

from app.errors import TokenExpired, InvalidGamingSession


from app import controller
from app.models import Client

from flask.ext.api.exceptions import AuthenticationFailed

'''TODO: check if request contains clientid, apikey and **valid** sessionid (will need to call the userprof svc)'''

@app.route('/gameevents/api/v1.0/token', methods = ['POST'])
def token():
    """The client can request an authentication token that will be used to 
    interact with the service. The POST request must be sent as JSON and include
    a valid "clientid" and "apikey" (unique for each game) and a valid "sessionid".
    The sessionid will be validated by the user profile service.       
    """

    #Check if request is json and contains all the required fields
    required_fields = ["clientid", "apikey", "sessionid"]
    if not request.json or not (set(required_fields).issubset(request.json)):        
        abort(status.HTTP_400_BAD_REQUEST, {'message': 'Invalid request. Please try again.'})
    else:
        clientid = request.json['clientid']
        sessionid = request.json['sessionid']
        apikey = request.json['apikey']
        
        try:
            token = controller.authenticate(clientid, apikey, sessionid)
            if token:
                return jsonify({ 'token': token.decode('ascii') })
            else:
                app.logger.debug("Could not authenticate, returning status 401.")
                return jsonify({'message': 'Could not authenticate.'}), status.HTTP_401_UNAUTHORIZED
        except AuthenticationFailed as e:
            app.logger.warning(e.args)
            abort(status.HTTP_401_UNAUTHORIZED, {'message': 'Could not authenticate. Please check your credentials and try again.'})
        except TokenExpired as e:
            abort(status.HTTP_401_UNAUTHORIZED, {'message': 'Your token expired. Please generate another one.'})
        except InvalidGamingSession as e:
            abort(status.HTTP_401_UNAUTHORIZED, {'message': 'Invalid gaming session. Did the player authorize the use of their data?'})
        except Exception as e:
            app.logger.error(e, exc_info=False)
            abort(status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@auth.verify_password
def verify_password(clientid_or_token, apikey=False, sessionid=False):
    try:
        return controller.authenticate(clientid_or_token, apikey, sessionid)
    except Exception as e:
        app.logger.error(e, exc_info=False)
        abort(status.HTTP_500_INTERNAL_SERVER_ERROR) # missing arguments  


@app.route('/gameevents/api/v1.0/client', methods = ['POST'])
def new_client():
    clientid = request.json.get('clientid')
    apikey = request.json.get('apikey')
    try:
        client = controller.newclient(clientid, apikey)
    except Exception as e:
        app.logger.error(e, exc_info=False)
        abort(status.HTTP_500_INTERNAL_SERVER_ERROR) # missing arguments
    #return jsonify({ 'clientid': client.clientid }), 201, {'Location': url_for('token', clientid = client.clientid, apikey = client.apikey, _external = True)}
    return jsonify({'message': 'Client ID created'}), status.HTTP_201_CREATED

'''
@app.route('/gameevents/api/v1.0/initsession', methods=['POST'])
def initsession():
    if not request.json or not 'id' in request.json:
        abort(status.HTTP_400_BAD_REQUEST)
    gamingsession = {
        'id': request.json['id'],
        'timestamp': str(datetime.datetime.now()),
        'status':'active'
    }
    controller.startgamingsession()
    return jsonify({'token': gamingsession}), status.HTTP_200_OK

@app.route('/gameevents/api/v1.0/endsession', methods=['POST'])
def endsession():
    if not request.json or not 'id' in request.json:
        abort(status.HTTP_400_BAD_REQUEST)
    if controller.finishgamingsession(request.json['id']):
        return jsonify({'message': 'Session terminated'}), status.HTTP_200_OK
    else:
        resp = make_response(json.dumps({'error': 'No such session.'}), status.HTTP_405_METHOD_NOT_ALLOWED)
        h = resp.headers
        h['Access-Control-Allow-Methods'] = 'initsession'        
        return resp
'''


@app.route('/gameevents/api/v1.0/commitevent', methods=['POST'])
def commitevent():
    """Receives a json request with an auth token, timestamp, and game event.
    token:
    """
    #Check if request is json and contains all the required fields
    required_fields = ["token", "gameevent", "timestamp"]
    if not request.json or not (set(required_fields).issubset(request.json)):        
        abort(status.HTTP_400_BAD_REQUEST, {'message': 'Invalid request. Please try again.'})
    else:    
        try:
            #app.logger.debug("trying to expire the token.")
            #time.sleep(5) #expire the token
            success = controller.recordgameevent(request.json['token'], request.json['timestamp'], request.json['gameevent']) 
            if success:
                app.logger.info("Successfully recorded a game event.")
                return jsonify({'message': "Game event recorded successfully."}), status.HTTP_201_CREATED
            else:
                app.logger.warning("Could not record game event.")
                abort(status.HTTP_500_INTERNAL_SERVER_ERROR)
            #    return jsonify({'message': 'Sorry, could not process your request.'}), status.HTTP_500_INTERNAL_SERVER_ERROR
        except AuthenticationFailed as e:
            app.logger.warning("Authentication failure when trying to record game event.")          
            abort(status.HTTP_401_UNAUTHORIZED, {'message': e.args}) # missing arguments   
        except Exception as e:
            app.logger.error("Undefined exception when trying to record a game event.")
            app.logger.error(e, exc_info=False)
            abort(status.HTTP_500_INTERNAL_SERVER_ERROR) 