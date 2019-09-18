from flask import Flask
from flask import render_template
from flask import request, render_template, flash, redirect, send_from_directory
import pandas as pd
from image_model import make_prediction
from petfinder_api import Petfinder
from werkzeug.utils import secure_filename
from image_model import make_prediction
import os
from dotenv import load_dotenv
load_dotenv('.env')
import numpy as np

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'JPEG', 'JPG'])
cwd = os.getcwd()

application = Flask(__name__)
application.secret_key = os.environ['FLASK_SECRET']
application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

pf = Petfinder()


# check file is ok
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initial page
@application.route('/', methods=['GET', 'POST'])
def index():
    return render_template("index.html")

# finding uploaded photos
@application.route('/uploads/<filename>')
def send_file(filename):
    print('served image:',os.path.join(cwd, UPLOAD_FOLDER, filename))
    return send_from_directory(os.path.join(cwd, UPLOAD_FOLDER), filename)

# method to purge all previous uploaded folders
@application.route('/purge', methods=['POST'])
def purge():
    uploads = os.listdir(os.path.join(cwd, UPLOAD_FOLDER))
    if len(uploads)>0:
        for image in uploads:
            os.remove(os.path.join(cwd, UPLOAD_FOLDER, image))

# called when user presses upload button
@application.route('/uploader', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')
            filepath = os.path.join(application.config['UPLOAD_FOLDER'], filename)
            zip = str(request.form['zip'])
            if (len(zip)!=5) or not zip.isdigit():
                return render_template("retry_input.html",
                                       message='Oops please enter a valid Zip')
            try:
                pred_df = make_prediction(filepath)
            except:
                return render_template("retry_input.html",
                                       message='''Sorry the breed classifier model is currently down.
                                       Blame Google and try again later''')
            if len(pred_df)==0:
                print('Oops please upload dog photos only')
                return render_template("retry_input.html",
                                       message = 'Oops please upload dog photos only')
            else:
                # print('top 4 breeds and probabilities')
                # print(pred_df.head())
                petfinder_recs = pf.get_dogs(pred_df,zip)
                if len(petfinder_recs)==0:
                    return render_template(
                        "retry_input.html",
                        message='''Sorry, no similar breeds found nearby or the Petfinder API connection is down.
                        Please try a different photo or come back later.'''
                    )
                return render_template("output.html",
                                       filename=filename,
                                       petfinder_recs=petfinder_recs,
                                       top_breeds=list(pred_df['pred_breed'].values)[:4]
                                       )
    return render_template("retry_input.html",
                           message='Oops please choose a valid jpg upload')

if __name__ == "__main__":
    # application.debug=True
    application.run()