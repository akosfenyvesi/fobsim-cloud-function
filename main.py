import functions_framework
import requests
import subprocess
import sys
import json
import json_utils
import os
import firebase_admin
from firebase_admin import credentials, db, storage
import re
import zipfile


cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://szte-edu-research-2023-default-rtdb.europe-west1.firebasedatabase.app/',
    'storageBucket': 'szte-edu-research-2023.appspot.com'
})


def cors_enabled_function(request):
    headers = {
        "Access-Control-Allow-Origin": "*"
    }

    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {
        "Access-Control-Allow-Origin": "*"
    }

    return run_simulation(request, headers)


@functions_framework.http
def run_simulation(request, headers=None):
    setup()
    uid = request.args.get('uid')
    timestamp = request.args.get('timestamp')
    settings = request.args.get('settings')
    extra_simulations = request.args.get('extraSimulations')
    print(extra_simulations)
    settings_dict = json_utils.filter_and_save(settings)

    messages_to_exclude = []
    with open("messages_to_exclude.json", "r") as f:
        messages_to_exclude.extend(json.load(f))

    start_simulation(uid, timestamp, settings_dict, messages_to_exclude)

    if extra_simulations:
        extra_simulations_list = json.loads(extra_simulations)
        for simulation_input in extra_simulations_list["inputs"]:
            json_utils.modify_json_value(extra_simulations_list["name"], simulation_input)
            start_simulation(uid, timestamp, settings_dict, messages_to_exclude)
            db.reference(f'/fobsim/users/{uid}/{timestamp}').update({'extraSimulations': extra_simulations})
        

    upload_temporyary_files(uid, timestamp)
    db.reference(f'/fobsim/users/{uid}/{timestamp}').update({'settings': settings})

    return ('OK', 200, headers)


def start_simulation(uid, timestamp, settings_dict, messages_to_exclude):
    ref = db.reference(f'/fobsim/users/{uid}/{timestamp}/temp')

    input_data = f"{settings_dict['function']}\n{settings_dict['placement']}\n{settings_dict['consensus_algorithm']}\n{settings_dict['ai_assisted_mining']}\n\n"

    process = subprocess.Popen([sys.executable or 'python', "./main_fobsim.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(input_data.encode())
    process.stdin.flush()

    buffer = ""
    while True:
        output = process.stdout.readline().decode('utf-8')
        print(output)
        if not output and process.poll() is not None:
            break

        if match := re.search(r'elapsed time = (\d+\.\d+) seconds', output):
            elapsed_time = float(match[1])
            results_ref = db.reference(f'/fobsim/users/{uid}/{timestamp}/results/elapsedTime')
            if elapsed_times := results_ref.get():
                elapsed_times.append(elapsed_time)
                results_ref.set(elapsed_times)
            else:
                db.reference(f'/fobsim/users/{uid}/{timestamp}/results').update({'elapsedTime': [elapsed_time]})

        if output not in messages_to_exclude:
            buffer += output

        if len(buffer) >= 500:
            publish_message(buffer, ref)
            buffer = ""

    remaining_output, remaining_err = process.communicate()

    if remaining_output:
        publish_message(remaining_output.decode('utf-8'), ref)

    publish_message('simulation_complete', ref)

def setup():
    directory = "temporary"
    if not os.path.exists(directory):
        os.makedirs(directory)


def publish_message(message, ref):
    ref.push().set({
        'message': message
    })


def upload_temporyary_files(uid, timestamp):
    temporary_dir = "temporary"
    zip_filename = "temporaryfiles.zip"

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for filename in os.listdir(temporary_dir):
            file_path = os.path.join(temporary_dir, filename)
            zipf.write(file_path, os.path.basename(file_path))

    bucket = storage.bucket()
    blob = bucket.blob(f'/fobsim/users/{uid}/{timestamp}/{zip_filename}')
    blob.upload_from_filename(zip_filename)

    download_url = blob.public_url
    ref = db.reference(f'/fobsim/users/{uid}/{timestamp}/files/temporaryfiles')
    ref.set(download_url)

    # Clean up temporary files
    os.remove(zip_filename)
    for filename in os.listdir(temporary_dir):
        file_path = os.path.join(temporary_dir, filename)
        os.remove(file_path)