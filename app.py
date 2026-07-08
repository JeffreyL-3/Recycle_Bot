from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from collections import defaultdict, deque
import os
from interface import simple_output
import requests
import shutil
import defaults
import math
import time


app = Flask(__name__)

# Configure folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GEOCODE_RATE_LIMIT_WINDOW_SECONDS = 60
GEOCODE_RATE_LIMIT_PER_IP = 20
GEOCODE_RATE_LIMIT_GLOBAL = 120
geocode_request_times_by_ip = defaultdict(deque)
geocode_global_request_times = deque()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def empty_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def extract_address_component(address_components, type_name, use_short_name=False):
    for component in address_components:
        if type_name in component.get('types', []):
            return component.get('short_name' if use_short_name else 'long_name', '')

    return ''

def extract_town_and_state(geocode_results):
    town_types = ['locality', 'postal_town', 'administrative_area_level_3', 'sublocality']

    for result in geocode_results:
        address_components = result.get('address_components', [])
        state = extract_address_component(address_components, 'administrative_area_level_1', True)

        for town_type in town_types:
            town = extract_address_component(address_components, town_type)
            if town and state:
                return town, state

    return '', ''

def validate_coordinates(latitude, longitude):
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return None, None

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None, None

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None, None

    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return None, None

    return latitude, longitude

def prune_request_times(request_times, now):
    while request_times and now - request_times[0] > GEOCODE_RATE_LIMIT_WINDOW_SECONDS:
        request_times.popleft()

def get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return request.remote_addr or 'unknown'

def is_geocode_rate_limited(client_ip):
    now = time.time()
    client_request_times = geocode_request_times_by_ip[client_ip]

    prune_request_times(client_request_times, now)
    prune_request_times(geocode_global_request_times, now)

    if len(client_request_times) >= GEOCODE_RATE_LIMIT_PER_IP:
        return True
    if len(geocode_global_request_times) >= GEOCODE_RATE_LIMIT_GLOBAL:
        return True

    client_request_times.append(now)
    geocode_global_request_times.append(now)
    return False

# Initial page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    data = request.get_json(silent=True) or {}
    latitude, longitude = validate_coordinates(data.get('latitude'), data.get('longitude'))

    if latitude is None or longitude is None:
        return jsonify({'error': 'Invalid latitude or longitude'}), 400

    if is_geocode_rate_limited(get_client_ip()):
        return jsonify({'error': 'Too many location lookup requests. Please try again later.'}), 429

    google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()
    if not google_maps_api_key:
        return jsonify({'error': 'GOOGLE_MAPS_API_KEY is not configured'}), 500

    params = {
        'latlng': str(latitude) + ',' + str(longitude),
        'key': google_maps_api_key,
        'result_type': 'locality|administrative_area_level_3|sublocality|administrative_area_level_1'
    }

    try:
        response = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=params, timeout=8)
    except requests.RequestException:
        return jsonify({'error': 'Location lookup failed'}), 502

    if response.status_code != 200:
        return jsonify({'error': 'Location lookup failed'}), 502

    try:
        geocode_response = response.json()
    except ValueError:
        return jsonify({'error': 'Location lookup failed'}), 502

    if geocode_response.get('status') != 'OK':
        return jsonify({'error': 'Location lookup failed'}), 502

    town, state = extract_town_and_state(geocode_response.get('results', []))
    if not town or not state:
        return jsonify({'error': 'Location lookup failed'}), 502

    return jsonify({'town': town, 'state': state})

#Dynamic page updates
@app.route('/process', methods=['POST'])
def process():
    start = time.time()
    empty_folder(app.config['UPLOAD_FOLDER'])

    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)

        # Get other form data

        api_key = request.form.get('api_key', '').strip()

        town = request.form.get('town', '')
        state = request.form.get('state', '')
        object = request.form.get('object', defaults.getDefaultObject())
        personality = request.form.get('personality', defaults.getDefaultPersonality())

        result_code, detected_object, header, details, *costOutput = simple_output(image_path, town, state, object, personality, api_key)
        
        end = time.time()
        timeTaken= end - start
        print("Query time: " + (str)(timeTaken) + " seconds")
        
        # Return JSON response
        return jsonify({
            'result_code': result_code, 
            'detected_object': detected_object,
            'header': header, 
            'details': details, 
            'costOutput': costOutput if costOutput else None
        })
    else:
        end = time.time()
        timeTaken= end - start
        print("Query time: " + (str)(timeTaken) + " seconds")
        
        return jsonify({'error': 'Invalid file format'}), 400
    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
