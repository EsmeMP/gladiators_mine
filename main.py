import psycopg2
from flask import Flask, request, redirect, render_template, jsonify, url_for, session, flash
# from flask_bootstrap import Bootstrap
# from flask_wtf import FlaskForm
# from wtforms.fields import PasswordField, StringField, SubmitField
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import db
# from flask_bcrypt import Bcrypt
# from forms import LibrosForm
import bcrypt
import os
from werkzeug.utils import secure_filename
from db import obtener_conexion, liberar_conexion




app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

UPLOAD_FOLDER = 'static/assets/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

products = {
    '21454': {'name': 'Producto 1', 'price': 100},
    '21455': {'name': 'Producto 2', 'price': 200},
}

    
@app.route('/')
# def hello():
#     return "Hello World"

# app.run (host = '0.0.0.0', port=3000)





@app.route('/seccion')
def seccion():
    return render_template('secciones.html')





@app.route('/registrar_venta')
def registrar_venta():
    conn =db.conectar()
    # crear un cursor (objeto para recorrer las tablas)
    cursor = conn.cursor()
    # ejecutar una consulta en postgres
    cursor.execute('''SELECT * FROM tabla_ventas''')
    #recuperar la informacion
    datos = cursor.fetchall()
    #cerrar cursos y conexion a la base de datos
    cursor.close()
    db.desconectar(conn)
    return render_template('regVenta.html', datos=datos)

@app.route('/get_product_details', methods=['GET'])
def get_product_details():
    code = request.args.get('code')
    product = products.get(code)
    if product:
        return jsonify(product)
    else:
        return jsonify({}), 404

@app.route('/confirmar_venta', methods=['POST'])
def confirmar_venta():
    ventas = request.json.get('ventas', [])
    # Aquí puedes procesar y almacenar la venta en tu base de datos
    # Ejemplo:
    for venta in ventas:
        # Procesar cada venta, agregar a la base de datos, etc.
        pass
    return jsonify({'message': 'Venta confirmada'}), 200



@app.route('/')
def index():
    return render_template('index.html')











# @app.route('/consultar_usuario')
# def consultar_usuario():
#     return render_template('consultarUsuario.html')

@app.route('/consultar_usuario/<int:id_usuario>')
def consultar_usuario(id_usuario):
    conn = db.conectar()
    cursor = conn.cursor()
    
    # Obtener información general del usuario desde la vista `nombre_usuario`
    cursor.execute('''SELECT * FROM nombre_usuario
                      WHERE "ID" = %s''', (id_usuario,))
    usuario_general = cursor.fetchone()
    
    # Obtener información específica del usuario desde la vista `info_especifica_user`
    cursor.execute('''SELECT * FROM info_especifica_user
                      WHERE "ID" = %s''', (id_usuario,))
    usuario_especifico = cursor.fetchone()

    cursor.close()
    db.desconectar(conn)
    
    # Combinar la información general y específica en un solo diccionario
    if usuario_general and usuario_especifico:
        usuario = usuario_general + usuario_especifico
    else:
        usuario = None
    
    return render_template('consultarUsuario.html', usuario=usuario)

@app.route('/consultar_usuarios')
def consultar_usuarios():
    conn =db.conectar()
    # crear un cursor (objeto para recorrer las tablas)
    cursor = conn.cursor()
    # ejecutar una consulta en postgres
    cursor.execute('''SELECT * FROM consulta_general''')
    #recuperar la informacion
    datos = cursor.fetchall()
    #cerrar cursos y conexion a la base de datos
    cursor.close()
    db.desconectar(conn)
    return render_template('consultarUsuarios.html', datos=datos)


# @app.route('/registrar_usuario')
# def registrar_usuario():
#     return render_template('regUsuario.html')



@app.route('/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if request.method == 'POST':
        # Comprobación de existencia de los campos
        required_fields = [
            'nombre', 'apellido_paterno', 'apellido_materno', 'domicilio', 
            'numero_telefonico', 'curp', 'date', 'correo_electronico', 
            'nombre_usuario', 'contraseña', 'tipos_de_usuario'
        ]
        
        for field in required_fields:
            if field not in request.form:
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        nombre = request.form['nombre']
        a_paterno = request.form['apellido_paterno']
        a_materno = request.form['apellido_materno']
        domicilio = request.form['domicilio']
        numero_telefono = request.form['numero_telefonico']
        curp = request.form['curp']
        fecha_contratacion = request.form['date']
        correo_electronico = request.form['correo_electronico']
        username = request.form['nombre_usuario']
        password = request.form['contraseña']
        rol = request.form['tipos_de_usuario']

        # Convertir rol a booleano
        rol_booleano = True if rol == 'administrador' else False

        file = request.files.get('imagen')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ruta_imagen = os.path.join('assets', 'img', filename).replace('\\', '/')
        else:
            ruta_imagen = 'assets/img/imagen_defecto.jpeg'

        conn = db.conectar()
        cur = conn.cursor()
        
        try:
            # Inicia una transacción
            cur.execute("BEGIN;")
            
            # Inserta en info_empleado y obtiene el ID generado
            cur.execute("""
                INSERT INTO info_empleado (nombre, a_paterno, a_materno, domicilio, numero_telefono, curp, fecha_contratacion, correo_electronico, imagen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_empleado;
            """, (nombre, a_paterno, a_materno, domicilio, numero_telefono, curp, fecha_contratacion, correo_electronico, ruta_imagen))
            
            resultado = cur.fetchone()
            if resultado:
                nuevo_id_empleado = resultado[0]
            else:
                raise Exception("No se pudo obtener el id_empleado generado.")
            
            # Inserta en usuario utilizando el ID generado
            cur.execute("""
                INSERT INTO usuario (fk_info_empleado, username, password, rol)
                VALUES (%s, %s, %s, %s);
            """, (nuevo_id_empleado, username, password, rol_booleano))
            
            # Finaliza la transacción
            cur.execute("COMMIT;")

            flash('Usuario registrado con éxito', 'success')

            return render_template('regUsuario.html')

        except Exception as e:
            # En caso de error, deshace la transacción
            flash(f'Error: {str(e)}', 'danger')
            return redirect('/registrar_usuario')

        finally:
            # Cierra el cursor y la conexión
            cur.close()
            db.desconectar(conn)
    else:
        return render_template('regUsuario.html')



# @app.route('/editar_usuario')
# def editar_usuario():
#     return render_template('editarUsuario.html')






# EDICION
@app.route('/update1_usuario/<int:id_usuario>', methods=['GET'])
def update1_usuario(id_usuario):
    conn = db.conectar()
    cursor = conn.cursor()

    # Utiliza la vista 'edicion_user' para obtener los datos necesarios
    cursor.execute('''SELECT * FROM info_especifica_user 
                   WHERE "ID" = %s''', (id_usuario,))
    
    datos = cursor.fetchone()
    cursor.close()
    db.desconectar(conn)
    
    return render_template('editarUsuario.html', datos=datos)

@app.route('/update_usuario_post/<int:id_usuario>', methods=['POST'])
def update_usuario_post(id_usuario):
    nombre = request.form['nombre']
    a_paterno = request.form['apellido_paterno']
    a_materno = request.form['apellido_materno']
    domicilio = request.form['domicilio']
    numero_telefono = request.form['numero_telefonico']
    curp = request.form['curp']
    fecha_contratacion = request.form['date']
    correo_electronico = request.form['correo_electronico']
    username = request.form['nombre_usuario']
    password = request.form['contraseña']
    rol = request.form['tipos_de_usuario']
    rol_booleano = True if rol == 'administrador' else False

    conn = db.conectar()
    cur = conn.cursor()

    try:
        # Manejar la subida del archivo
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                ruta_imagen = os.path.join('assets', 'img', filename).replace('\\', '/')
                cur.execute('''
                    UPDATE info_empleado
                    SET nombre=%s, a_paterno=%s, a_materno=%s, domicilio=%s, numero_telefono=%s, curp=%s, fecha_contratacion=%s, correo_electronico=%s, imagen=%s
                    FROM usuario
                    WHERE info_empleado.id_empleado = usuario.fk_info_empleado
                    AND usuario.id_usuario = %s
                ''', (nombre, a_paterno, a_materno, domicilio, numero_telefono, curp, fecha_contratacion, correo_electronico, ruta_imagen, id_usuario))
            else:
                cur.execute('''
                    UPDATE info_empleado
                    SET nombre=%s, a_paterno=%s, a_materno=%s, domicilio=%s, numero_telefono=%s, curp=%s, fecha_contratacion=%s, correo_electronico=%s
                    FROM usuario
                    WHERE info_empleado.id_empleado = usuario.fk_info_empleado
                    AND usuario.id_usuario = %s
                ''', (nombre, a_paterno, a_materno, domicilio, numero_telefono, curp, fecha_contratacion, correo_electronico, id_usuario))
        else:
            cur.execute('''
                UPDATE info_empleado
                SET nombre=%s, a_paterno=%s, a_materno=%s, domicilio=%s, numero_telefono=%s, curp=%s, fecha_contratacion=%s, correo_electronico=%s
                FROM usuario
                WHERE info_empleado.id_empleado = usuario.fk_info_empleado
                AND usuario.id_usuario = %s
            ''', (nombre, a_paterno, a_materno, domicilio, numero_telefono, curp, fecha_contratacion, correo_electronico, id_usuario))
        
        cur.execute('''
            UPDATE usuario
            SET username=%s, password=%s, rol=%s
            WHERE id_usuario=%s
        ''', (username, password, rol_booleano, id_usuario))

        conn.commit()
        return redirect(url_for('consultar_usuarios'))

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        db.desconectar(conn)



# CODIGO PIÑA
#eliminar usuario
@app.route('/delete_usuario/<int:id_usuario>', methods=['POST'])
def delete_usuario(id_usuario):
    conn = db.conectar()
    cursor = conn.cursor()
    try:
        # Obtener el fk_info_empleado antes de eliminar el usuario
        cursor.execute('''SELECT fk_info_empleado FROM usuario WHERE id_usuario = %s''', (id_usuario,))
        fk_info_empleado = cursor.fetchone()[0]
        
        # Borrar el usuario de la tabla usuario
        cursor.execute('''DELETE FROM usuario WHERE id_usuario = %s''', (id_usuario,))
        
        # Borrar el registro correspondiente en la tabla info_empleado
        cursor.execute('''DELETE FROM info_empleado WHERE id_empleado = %s''', (fk_info_empleado,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar usuario: {e}")
    finally:
        cursor.close()
        db.desconectar(conn)
    
    return redirect(url_for('consultar_usuarios'))




#TE MANDA A EDITAR
# @app.route('/update1_usuario/<int:id_usuario>', methods= ['POST'])
# def update1_usuario(id_usuario):
#     conn =db.conectar()

#     cursor=conn.cursor()
#     cursor.execute('''SELECT * FROM usuario WHERE id_usuario=%s''',(id_usuario,))
#     datos = cursor.fetchall()
#     cursor.close()
#     db.desconectar(conn)
#     return render_template('editar_usuario.html',datos=datos)


#TE MANDA A ELIMINAR
# @app.route('/update2_usuario/<int:id_usuario>', methods= ['POST'])
# def update2_usuario(id_usuario):
#     nombre = request.form['nombre']
#     conn =db.conectar()

#     #crear un cursor (objeto para recorrer las tablas)#
#     cursor=conn.cursor()
#     cursor.execute('''UPDATE usuario SET username=%s WHERE id_usuario=%s''', (nombre, id_usuario,))
#     conn.commit()
#     cursor.close()
#     db.desconectar(conn)
#     return redirect(url_for('index'))


# buscar usuario
@app.route('/buscar_usuario', methods=['POST'])
def buscar_usuario():
    buscar_texto = request.form['buscar']
    #conectar con la BD
    conn= db.conectar()
    #crear un cursor (objeto para recorrer las tablas)
    cursor= conn.cursor()
    cursor.execute('''SELECT * FROM usuario WHERE username ILIKE %s OR id_usuario::TEXT ILIKE %s''', (f'%{buscar_texto}%', f'%{buscar_texto}%'))
    datos = cursor.fetchall()
    cursor.close()
    db.desconectar(conn)
    return render_template('consultarUsuarios.html', datos=datos)


