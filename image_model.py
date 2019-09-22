import numpy as np
import pandas as pd
import requests
import json
import os
from tensorflow.keras.applications.xception import preprocess_input as xception_preprocessor
from tensorflow.keras.applications.densenet import preprocess_input as densenet_preprocessor
from tensorflow.keras.preprocessing import image
from dotenv import load_dotenv

load_dotenv('.env')

DOGDETECTOR_MODEL_URL = os.environ['DOGDETECTOR_MODEL_URL']
BREED_MODEL_URL = os.environ['BREED_MODEL_URL']

image_size = 224
targets = pd.read_csv('breeds_list_new.csv', header=None, squeeze=True).tolist()
num_classes = len(targets) + 1

def path_to_tensor(img_path, preprocessor, display_image=False):
    img = image.load_img(img_path, target_size=((image_size, image_size)))
    img = image.img_to_array(img)
    img = np.expand_dims(img, axis=0)  # adds a 4th dimension that is essentially batchsize=1
    return preprocessor(img)

def dog_detector(path, display_image=False):
    img = path_to_tensor(path, display_image=display_image, preprocessor=densenet_preprocessor)
    payload = {
        "instances": [{'input_image': img.reshape(image_size, image_size, 3).tolist()}],
        "signature_name": "serving_default"
    }
    r = requests.post(DOGDETECTOR_MODEL_URL, json=payload)
    prediction = np.array(json.loads(r.text)['predictions']).argmax()
    return (prediction <= 268) & (prediction >= 151)

def make_prediction(path):
    print('loading image')
    img = path_to_tensor(path, display_image=True, preprocessor=xception_preprocessor)

    # first see if it's a dog or not
    if dog_detector(path):
        print("It looks like you're a dog, let's see which breed!")
    else:
        print("You don't look like a dog, maybe a human? Let's see what kind of dog you would be!")
        return pd.DataFrame()

    payload = {
        "instances": [{'input_image': img.reshape(image_size, image_size, 3).tolist()}],
        "signature_name": "serving_default"
    }
    r = requests.post(BREED_MODEL_URL, json=payload)
    prediction = json.loads(r.text)['predictions']
    pred_df = pd.Series(prediction[0]).sort_values(ascending=False).to_frame(name='pred_proba')
    pred_df['pred_breed'] = [targets[i] for i in pred_df.index]
    return pred_df
