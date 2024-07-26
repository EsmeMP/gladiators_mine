import psycopg2
from flask import Flask, request, redirect, render_template, url_for
# from flask_bootstrap import Bootstrap
# from flask_wtf import FlaskForm
# from wtforms.fields import PasswordField, StringField, SubmitField
import db
# from forms import LibrosForm


app = Flask(__name__)

@app.route('/')
# def hello():
#     return "Hello World"

# app.run (host = '0.0.0.0', port=3000)

@app.route('/regVenta')
def venta():
    conn =db.conectar()
    # crear un cursor (objeto para recorrer las tablas)
    cursor = conn.cursor()
    # ejecutar una consulta en postgres
    cursor.execute('''SELECT * FROM venta''')
    #recuperar la informacion
    datos = cursor.fetchall()
    #cerrar cursos y conexion a la base de datos
    cursor.close()
    db.desconectar(conn)
    return render_template('regVenta.html', datos=datos)

@app.route('/consultar_usuario')
def consultar_usuario():
    return render_template('consultarUsuario.html')

@app.route('/registrar_usuario')
def registrar_usuario():
    return render_template('regUsuario.html')

