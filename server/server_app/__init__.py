from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary

app = Flask(__name__)
app.secret_key = 'IYRV%$DWvbignyhuiojNJGUBFKHJhjkFVHkbj*&tuy'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin%40123@localhost/clinic_db?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_ECHO'] = True
app.config['PAGE_SIZE']= 111111115

db = SQLAlchemy(app=app)
login = LoginManager(app=app)

cloudinary.config(
    cloud_name = 'djga3njzi',
    api_key = '595946198281489',
    api_secret = 'hd1cRj177f0HVAQ-vSeqG_yT9Y0'
)

# # Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client
#
# # Set environment variables for your credentials
# Read more at http://twil.io/secure
account_sid = "AC645668ca4d9314c4f1a9d9b14476f75a"
auth_token = "797175bd8d82df462db857d1e741f302"
verify_sid = "VA27569bc38b3bd9bc6f1da165e44bb848"
# verified_number = "+84866135147"

client = Client(account_sid, auth_token)