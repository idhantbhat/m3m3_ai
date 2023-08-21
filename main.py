import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for
import jwt
import os
import random
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
import time
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
API_KEY = os.getenv('API_KEY')



app = Flask(__name__)

TEMPLATES_CONFIG = {
    "1": {
        "overlay_resize": (425, 425),
        "overlay_position": (440, 440),
        "text_position": (480, 440),
    },
    "2": {
        "overlay_resize": (425, 425),
        "overlay_position": (640, 180),
        "text_position": (232, 50),
    },
    "3": {
        "overlay_resize": (820, 820),
        "overlay_position": (100, 214),
        "text_position": (81, 26),
    }
}

def delayed_delete(overlay_image_pathAPI, output_path):
    time.sleep(30)  # Delay for 30 seconds
    try:
        os.remove(overlay_image_pathAPI)
    except Exception as e:
        print(f"Failed to delete {overlay_image_pathAPI}. Reason: {e}")
    try:
        os.remove(output_path)
    except Exception as e:
        print(f"Failed to delete {output_path}. Reason: {e}")

def overlay_text_on_template(template_path, output_path, user_text, overlay_image_path, template_config):
    template = Image.open(template_path)
    overlay = Image.open(overlay_image_path)
    if overlay.mode != 'RGBA':
        overlay = overlay.convert('RGBA')
    overlay = overlay.resize(template_config["overlay_resize"])
    template.paste(overlay, template_config["overlay_position"], overlay)
    draw = ImageDraw.Draw(template)
    font = ImageFont.truetype("arial.ttf", size=50)
    draw.text(template_config["text_position"], user_text, font=font, fill="black")
    template.save(output_path)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def upload():
    body = request.form.get('body')
    text = request.form.get('text')
    template_number = request.form.get('template-number')
    api_key = request.form.get('api-key')

    data = {
        "body": body,
        "text": text,
        "template_number": template_number,
        "api_key": api_key
    }

    jwt_token = jwt.encode(data, SECRET_KEY, algorithm='HS256')
    return redirect(url_for('generate', jwt_token=jwt_token))


@app.route("/generate/<jwt_token>")
def generate(jwt_token):
    data = jwt.decode(jwt_token, SECRET_KEY, algorithms=['HS256'])
    num = random.randint(10 ** 9, 10 ** 10 - 1)
    prompt_text = data.get('body')
    text = data.get('text')
    template_number = data.get('template_number')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "prompt": prompt_text,
        "n": 1,
        "size": "1024x1024"
    }
    response = requests.post(
        'https://api.openai.com/v1/images/generations',
        headers=headers,
        json=payload,
        timeout=20
    )
    if response.status_code == 200:
        print('first check')
        openai_response = response.json()
        image_url = openai_response['data'][0]['url']
        image_response = requests.get(image_url)
        print('secondcheck')
        overlay_image_pathAPI = os.path.join('PictureTemplates', f'{num}.jpg')
        with open(overlay_image_pathAPI, 'wb') as img_file:
            img_file.write(image_response.content)
        overlay_image_path = rf'C:\Users\amogus\PycharmProjects\pythonProject9\PictureTemplates\{num}.jpg'
        template_path = os.path.join('PictureTemplates', f'template{template_number}.jpg')
        output_path = os.path.join('static', f'{num}.jpg')
        overlay_text_on_template(template_path, output_path, text, overlay_image_path,
                                 TEMPLATES_CONFIG[template_number])
        thread = Thread(target=delayed_delete, args=(overlay_image_pathAPI, output_path))
        thread.start()
        return render_template('generated.html', image_url=url_for('static', filename=f'{num}.jpg'))
    else:
        return jsonify({"error": "Failed to generate image"}), 500

if __name__ == "__main__":
    app.run(debug=True)
