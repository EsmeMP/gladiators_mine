import psycopg2
from flask import Flask, redirect, render_template


app = Flask(__name__)

@app.route('/')
# def hello():
#     return "Hello World"

# app.run (host = '0.0.0.0', port=3000)

@app.route('/venta')
def venta():
    # Conectar con la base de datos
    conexion = psycopg2.connect(
        database="database_gladiators",
        user="first_gladiator",
        password="gladiator1st",
        host="localhost",
        port="5432"
    )
    # crear un cursor (objeto para recorrer las tablas)
    cursor = conexion.cursor()
    # ejecutar una consulta en postgres
    cursor.execute('''SELECT * FROM venta''')
    #recuperar la informacion
    datos = cursor.fetchall()
    #cerrar cursos y conexion a la base de datos
    cursor.close()
    conexion.close()
    return render_template('regVenta.html', datos=datos)  

# @app.route('/consultarUsuario')
# def consultarUsuario():
#     conexion = psycopg2.connect(
#         database="database_gladiators",
#         user="first_gladiator",
#         password="gladiator1st",
#         host="localhost",
#         port="5432"
#     )

# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=3000)

# @app.route('/consultarUsuario')
# def consultarUsuario():
#     return render_template('consultarUsuario.html', datos=datos)

# @app.route('/productos')
# def productos():
#     return render_template('pages/productos.html')

# if __name__ == '__main__':
#     app.run(debug=True)