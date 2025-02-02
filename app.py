# -*- coding: utf-8 -*-
from flask import Flask, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal, ROUND_HALF_UP
import os
import json
import recipeSearch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///frire.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class FrireUsers(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  username = db.Column(db.String(30), nullable=False, unique=True)
  password = db.Column(db.String(100), nullable=False)

class FridgeItem(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  itemName = db.Column(db.String(30), nullable=False)
  itemNum = db.Column(db.Integer, nullable=False)
  itemCost = db.Column(db.Integer)
  expiryDate = db.Column(db.DateTime, nullable=False)
  userid = db.Column(db.Integer, nullable=False)

class Recipes(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  recipeName = db.Column(db.String(30), nullable=False)
  cookTime = db.Column(db.String(10), nullable=False)
  material = db.Column(db.String(100), nullable=False)
  recipeImg = db.Column(db.String(255))
  recommendPoint = db.Column(db.Float, nullable=False)
  expiryDate = db.Column(db.DateTime, nullable=False)
  userid = db.Column(db.Integer, nullable=False)

onClick = 0
value = None

@login_manager.user_loader
def load_user(user_id):
  return FrireUsers.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
  return redirect('/login')

@app.route('/')
@login_required
def index():
  menu_titles = {'fridgeItem':"冷蔵庫の中身", 'recipe':"レシピ", 'calender':"食事カレンダー", 'goal':"あなたの目標", 'create':"食材登録", 'cost':"食材費"}
  return render_template('index.html', menu_titles=menu_titles, username=session["username"])

@app.route('/signup', methods=['GET','POST'])
def signup():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')

    user = FrireUsers(username=username, password=generate_password_hash(password, method='sha256'))

    db.session.add(user)
    db.session.commit()
    return redirect('/login')
  else:
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')

    user = FrireUsers.query.filter_by(username=username).first()
    if check_password_hash(user.password, password):
      session.permanent = True
      session["userid"] = user.id
      session["username"] = user.username
      login_user(user)
      return redirect('/')
  else:
    if "user" in session:
      return redirect('/')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
  session.pop('id',None)
  session.clear()
  logout_user()
  return redirect('/login')

@app.route('/fridgeItem', methods=['GET','POST'])
@login_required
def fridgeItem():
  userid = session["userid"]
  if request.method == 'GET':
    posts = FridgeItem.query.filter_by(userid=userid).all()
    return render_template('fridgeItem.html', posts=posts, username=session["username"])
  else:
    itemName = request.form.get('itemName')
    itemNum = request.form.get('itemNum')
    itemCost = request.form.get('itemCost')
    expiryDate = request.form.get('expiryDate')

    expiryDate = datetime.strptime(expiryDate, '%Y-%m-%d')
    new_post = FridgeItem(itemName=itemName, itemNum=itemNum, itemCost=itemCost, expiryDate=expiryDate, userid=userid)

    db.session.add(new_post)
    db.session.commit()
    recipeSearch.recipe_update(db, FridgeItem, Recipes, userid)
    return redirect('/fridgeItem')

@app.route('/updatefridgeItem', methods=['POST'])
@login_required
def updateFridgeItem():
  userid = session["userid"]
  itemName = request.form.get('itemName')
  itemNum = request.form.get('itemNum')
  itemCost = request.form.get('itemCost')
  expiryDate = request.form.get('expiryDate')
  expiryDate = datetime.strptime(expiryDate, '%Y-%m-%d')

  fridgeItems = FridgeItem.query.filter_by(userid=userid, itemName=itemName).all()
  
  for fridgeItem in fridgeItems:
    fridgeItem.itemName = itemName
    fridgeItem.itemNum = itemNum
    fridgeItem.itemCost = itemCost
    fridgeItem.expiryDate = expiryDate

  db.session.commit()
  return redirect('/fridgeItem')

@app.route('/create')
@login_required
def create():
  return render_template('create.html', username=session["username"])

@app.route('/recipe', methods=['GET','POST'])
@login_required
def recipe():
  global onClick
  global value

  userid = session["userid"]
  
  if request.method == 'GET':
    if onClick == 1:
      posts = Recipes.query.filter_by(userid=userid).order_by(desc(Recipes.recommendPoint)).all()
      onClick = 0
    else:
      posts = Recipes.query.filter_by(userid=userid).order_by(Recipes.expiryDate).all()
    
    feellists = {'あっさり':'Plain meal','重め':'Heavy meal','軽め':'Light meal','さっぱり':'Healthy','しょっぱい':'Salty','甘い':'Sweet','辛め':'Spicy','酸っぱい':'Sour','脂っこい':'Greasy'}

    feelButtons = []
    for feel_key, feel_value in feellists.items():
      feel = f'<button class="feel_button" type="submit" name="action" value="{feel_value}" onclick="isclick()"> { feel_key } </button>' 
      feelButtons.append(feel)
    
    feel_key = []
    if value != None:
      feel_key = [k for k, v in feellists.items() if v == value]
    else:
      feel_key.append("")
    
    return render_template('recipe.html', recipe_items = posts, feelButtons = feelButtons, youTaste = feel_key[0], username=session["username"])
  else:
    onClick = 1
    value = request.values["action"]
    recipe_items = Recipes.query.filter_by(userid=userid).all()
    
    with open('frire_data/recipes_feat.json') as fr:
      recipes_feat = json.load(fr)

    results = []
    for recipe_item in recipe_items:
      if recipes_feat.get(recipe_item.recipeName) == None:
        feat = 0
      else:
        feat = recipes_feat.get(recipe_item.recipeName).get(value)
        feat = Decimal(feat).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) 
      results.append(feat)

    for result, recipe_item in zip(results,recipe_items):
      recommendPoint = result
      recipe_item.recommendPoint = recommendPoint
    db.session.commit()
      
    return redirect('/recipe')

if __name__ == '__main__':
  app.run(debug=True)