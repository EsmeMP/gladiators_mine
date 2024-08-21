import psycopg2
from flask import Flask, request, redirect, render_template, jsonify, url_for, session, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
# from wtforms.fields import PasswordField, StringField, SubmitField
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import db
# from flask_bcrypt import Bcrypt
# from forms import LibrosForm
import bcrypt
import os
from werkzeug.utils import secure_filename
from db import obtener_conexion, liberar_conexion
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, make_response
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer
import itsdangerous
import json
from db import conectar, desconectar 




app = Flask(__name__)
app.secret_key = 'super_secret_key'
serializer = URLSafeTimedSerializer(app.secret_key)


def verificar_credenciales(username, password):
    connection = None
    try:
        connection = psycopg2.connect(
            user="first_gladiator",
            password="gladiator1st",
            host="localhost",
            port="5432",
            database="database_gladiators"
        )
        cursor = connection.cursor()
        query = "SELECT * FROM datos_login WHERE username = %s"
        cursor.execute(query, (username,))
        resultado = cursor.fetchone()

        if resultado:
            stored_password = resultado[3]  # Asumiendo que el password es el cuarto campo en el resultado
            if check_password_hash(stored_password, password):
                return resultado  # Devuelve toda la tupla
        return None


    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a la base de datos", error)
        return None

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = request.form.get('remember')  # Obtener la opción "Recuérdame"

        resultado = verificar_credenciales(username, password)
        if resultado is not None:
            session['usuario_id'] = resultado[0]
            session['nombre_completo'] = resultado[1]
            session['username'] = resultado[2]
            session['rol'] = resultado[4]
            if remember_me:
                token = serializer.dumps(username, salt='remember-me')
                response = make_response(redirect(url_for('secciones')))
                response.set_cookie('remember_token', token, max_age=60*60*24*30)  # Expira en 30 días
                return response
            return redirect(url_for('secciones'))
        else:
            flash("Usuario o contraseña incorrectos")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.before_request
def load_logged_in_user():
    if 'username' not in session:
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            try:
                username = serializer.loads(remember_token, salt='remember-me', max_age=60*60*24*30)
                session['username'] = username
            except:
                pass



# --------------------------------------------SECCIONES------------------------------------------------------------------

@app.route('/secciones')
def secciones():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        return render_template('secciones.html', username=username, rol=rol)
    else:
        return redirect(url_for('login'))



# ---------------------------------PRODUCTOS-----------------------------------------------------------------------------
@app.route('/productos')
def productos():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        if rol or request.endpoint in ['productos', 'ventas']:  # Administradores y cajeros
            return render_template('regProduct.html', username=username, rol=rol)
        else:
            flash("No tienes permisos para acceder a esta sección")
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))

# ---------------------------------------------------------VENTAS---------------------------------------------------------------



@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    conn = conectar()  # Obtener una conexión desde el pool
    cursor = conn.cursor()

    numero_venta = None
    total = 0.0  # Inicializar total

    if request.method == 'POST':
        try:
            venta_actual = request.form.get('venta_actual')
            if venta_actual:
                venta_actual = json.loads(venta_actual)
                print("Productos en la venta actual:", venta_actual)  # Debug

                if not venta_actual:
                    flash("No hay productos en la venta actual.")
                    return redirect(url_for('registrar_venta'))

                fk_usuario = session.get('usuario_id')
                if fk_usuario is None:
                    flash("Error: Usuario no autenticado.")
                    return redirect(url_for('login'))

                cursor.execute(
                    "INSERT INTO venta (fecha_venta, hora_venta, fk_usuario) VALUES (CURRENT_DATE, CURRENT_TIME, %s) RETURNING id_venta",
                    (fk_usuario,)
                )
                id_venta = cursor.fetchone()[0]
                print("ID de la nueva venta:", id_venta)  # Debug

                for item in venta_actual:
                    # Obtener id_producto a partir del codigo_barras
                    cursor.execute("SELECT id_producto FROM producto WHERE codigo_barras = %s", (item['code'],))
                    id_producto = cursor.fetchone()
                    
                    if id_producto:
                        id_producto = id_producto[0]
                    else:
                        flash(f"Producto con código {item['code']} no encontrado.")
                        conn.rollback()
                        return redirect(url_for('registrar_venta'))

                    # Insertar en detalle_venta usando id_producto
                    cursor.execute(
                        "INSERT INTO detalle_venta (cantidad, fk_producto, fk_venta) VALUES (%s, %s, %s)",
                        (item['quantity'], id_producto, id_venta)
                    )
                    print(f"Insertado en detalle_venta: cantidad={item['quantity']}, fk_producto={id_producto}, fk_venta={id_venta}")

                    # Calcular total
                    total += item['quantity'] * item['price']  # Usa el precio de la venta actual

                conn.commit()
                flash("Venta registrada exitosamente.", "success")
                session['venta_actual'] = []
                return redirect(url_for('venta_confirmada', id_venta=id_venta))

            else:
                flash("No hay productos en la venta actual.")
                return redirect(url_for('registrar_venta'))

        except Exception as e:
            conn.rollback()
            flash(f"Error al registrar la venta: {e}", "danger")
            print(f"Error al registrar la venta: {e}")
            return redirect(url_for('registrar_venta'))

        finally:
            cursor.close()
            desconectar(conn)  # Liberar la conexión de nuevo al pool

    else:  # Para método GET
        cursor.execute("SELECT COALESCE(MAX(id_venta) + 1, 1) FROM venta")
        numero_venta = cursor.fetchone()[0]

    cursor.close()
    desconectar(conn)  # Liberar la conexión de nuevo al pool

    return render_template('regVenta.html', numero_venta=numero_venta, total=total)





@app.route('/venta_confirmada')
def venta_confirmada():
    numero_venta = request.args.get('id_venta')
    fecha = request.args.get('fecha')
    hora = request.args.get('hora')
    usuario = request.args.get('usuario')
    total = request.args.get('total')

    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0.0

    return render_template('venta_confirmada.html', numero_venta=numero_venta, fecha=fecha, hora=hora, usuario=usuario, total=total)


@app.route('/get_product_details', methods=['GET'])
def get_product_details():
    code = request.args.get('code')
    product = obtener_producto_de_db(code)
    if product:
        return jsonify(product)
    else:
        return jsonify({}), 404


def obtener_producto_de_db(codigo):
    conn = db.conectar()
    cursor = conn.cursor()
    
    query = "SELECT nombre, precio FROM producto WHERE codigo_barras = %s"
    cursor.execute(query, (codigo,))
    
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()

    if resultado:
        nombre, precio = resultado
        return {'name': nombre, 'price': float(precio)}
    else:
        return None



@app.route('/reporte_diario')
def reporte_diario():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        # Permitir acceso a usuarios con rol 1 (administrador) o rol 2 (cajero)
        if rol in [1, 2]:
            fecha = request.args.get('fecha')
            # Obtiene la fecha seleccionada del formulario
            print(f"Fecha seleccionada: {fecha}")
            conn = db.conectar()
            cursor = conn.cursor()
            
            if fecha:
                # Realiza la consulta filtrando por la fecha seleccionada
                cursor.execute('''
                    SELECT *
                    FROM reporte_diario
                    WHERE fecha = %s
                ''', (fecha,))
            else:
                # Si no se ha seleccionado una fecha, muestra todas las ventas
                cursor.execute('SELECT * FROM reporte_diario')
            
            datos = cursor.fetchall()
            
            if datos:
                # Calcular el total de las ventas
                total = sum([fila[3] for fila in datos])
            else:
                total = 0
            
            cursor.close()
            db.desconectar(conn)
            
            # Renderiza la plantilla con los datos del reporte diario y el total
            return render_template('repDiario.html', datos=datos, total=total)
        else:
            return jsonify({"error": "Acceso no autorizado"}), 403
    else:
        return redirect(url_for('login'))


@app.route('/reporte_semanal', methods=['GET'])
def reporte_semanal():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        # Permitir acceso a usuarios con rol 1 (administrador) o rol 2 (cajero)
        if rol in [1, 2]:
            fecha1 = request.args.get('fecha1')
            fecha2 = request.args.get('fecha2')
            # Obtiene las fechas seleccionadas del formulario
            conn = db.conectar()
            cursor = conn.cursor()
            
            if fecha1 and fecha2:
                # Realiza la consulta filtrando por el rango de fechas seleccionado
                cursor.execute('''
                    SELECT * FROM reporte_diario
                    WHERE fecha BETWEEN %s AND %s
                ''', (fecha1, fecha2,))
            else:
                # Si no se han seleccionado fechas, muestra todas las ventas
                cursor.execute('SELECT * FROM reporte_diario')
            
            datos = cursor.fetchall()
            
            if datos:
                # Calcular el total de las ventas
                total = sum([fila[3] for fila in datos])
            else:
                total = 0
            
            cursor.close()
            db.desconectar(conn)
            
            # Renderiza la plantilla con los datos del reporte semanal y el total
            return render_template('repSemanal.html', datos=datos, total=total)
        else:
            return jsonify({"error": "Acceso no autorizado"}), 403
    else:
        return redirect(url_for('login'))



@app.route('/consulta_venta/<int:id>')
def consulta_venta(id):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        # Permitir acceso a usuarios con rol 1 (administrador) o rol 2 (cajero)
        if rol in [1, 2]:
            conn = db.conectar()
            cursor = conn.cursor()

            # Ejecutar la función en PostgreSQL
            cursor.execute('SELECT * FROM ventas_por_id(%s)', (id,))
            venta_especifica = cursor.fetchall()  # Obtener todas las filas de la venta específica

            cursor.execute('''SELECT id, fecha, hora, total_compra, "Nombre de Empleado"
                            FROM reporte_diario
                            WHERE id = %s''', (id,))
            venta_general = cursor.fetchone()  # Obtener una fila con la información general

            cursor.close()
            db.desconectar(conn)

            venta = {
                "especifica": venta_especifica if venta_especifica else None,
                "general": venta_general if venta_general else None
            }

            return render_template('consultaVenta.html', venta=venta)
        else:
            return jsonify({"error": "Acceso no autorizado"}), 403
    else:
        return redirect(url_for('login'))



# ---------------------------------------USUARIOS--------------------------------------------
@app.route('/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        if rol ==1 :  # Solo administradores
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

                    return render_template('regUsuario.html', username=username, rol=rol)

                except Exception as e:
                    # En caso de error, deshace la transacción
                    cur.execute("ROLLBACK;")
                    flash(f'Error: {str(e)}', 'danger')
                    return redirect('/registrar_usuario')

                finally:
                    # Cierra el cursor y la conexión
                    cur.close()
                    db.desconectar(conn)
            else:
                return render_template('regUsuario.html', username=username, rol=rol)
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('secciones'))
    


@app.route('/consultar_usuarios')
def consultar_usuarios():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        # Conectar a la base de datos
        conn = db.conectar()
        cursor = conn.cursor()
        
        # Ejecutar consulta en PostgreSQL
        cursor.execute('SELECT * FROM consulta_general')
        datos = cursor.fetchall()
        
        # Cerrar cursor y conexión
        cursor.close()
        db.desconectar(conn)
        
        # Renderizar la plantilla con datos del usuario y resultados de la consulta
        return render_template('consultarUsuarios.html', username=username, rol=rol, datos=datos)
    else:
        return redirect(url_for('secciones'))



@app.route('/update1_usuario/<int:id_usuario>', methods=['GET'])
def update1_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        if rol == 1:  # Solo administradores (rol == 1)
            # Conectar a la base de datos
            conn = db.conectar()
            cursor = conn.cursor()
            
            # Utiliza la vista 'edicion_user' para obtener los datos necesarios
            cursor.execute('''SELECT * FROM info_especifica_user 
                              WHERE "ID" = %s''', (id_usuario,))
            
            datos = cursor.fetchone()
            
            # Cerrar cursor y conexión
            cursor.close()
            db.desconectar(conn)
            
            # Renderizar la plantilla con datos del usuario y los datos obtenidos
            return render_template('editarUsuario.html', username=username, rol=rol, datos=datos)
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_usuarios'))
    else:
        return redirect(url_for('secciones'))


@app.route('/update_usuario_post/<int:id_usuario>', methods=['POST'])
def update_usuario_post(id_usuario):
    if 'username' in session and 'rol' in session:
        session_username = session['username']
        session_rol = session['rol']
        
        # Verificar que el rol sea 1 (administrador)
        if session_rol != 1:
            return jsonify({"error": "Acceso no autorizado"}), 403
        
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
    else:
        return redirect(url_for('secciones'))



@app.route('/buscar_usuario', methods=['POST'])
def buscar_usuario():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        # Permitir acceso a usuarios con rol 1 (administrador) o rol 2 (cajero)
        if rol in [1, 2]:  # Si el rol es 1 o 2, se permite el acceso
            buscar_texto = request.form['buscar']
            
            # Conectar a la base de datos
            conn = db.conectar()
            cursor = conn.cursor()
            
            # Ejecutar consulta en PostgreSQL
            cursor.execute('''
                SELECT * FROM usuario
                WHERE username ILIKE %s OR id_usuario::TEXT ILIKE %s
            ''', (f'%{buscar_texto}%', f'%{buscar_texto}%'))
            
            # Recuperar la información
            datos = cursor.fetchall()
            
            # Cerrar cursor y conexión
            cursor.close()
            db.desconectar(conn)
            
            # Renderizar la plantilla con los resultados de la búsqueda y los datos del usuario
            return render_template('consultarUsuarios.html', username=username, rol=rol, datos=datos)
        else:
            return jsonify({"error": "Acceso no autorizado"}), 403
    else:
        return redirect(url_for('login'))


# ------------------------------SOPORTE--------------------------------------------
@app.route('/soporte')
def soporte():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        if rol:  # Solo administradores
            return render_template('soporte.html', username=username, rol=rol)
        else:
            flash("No tienes permisos para acceder a esta sección")
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))

def agregar_usuario(username, password, rol):
    hashed_password = generate_password_hash(password)

    connection = None
    try:
        connection = psycopg2.connect(
            user="first_gladiator",
            password="gladiator1st",
            host="localhost",
            port="5432",
            database="database_gladiators"
        )
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO usuario (username, password, rol) VALUES (%s, %s, %s)",
            (username, hashed_password, rol)
        )
        connection.commit()
        print("Usuario agregado exitosamente")

    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a la base de datos", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario_view():
    username = request.form['username']
    password = request.form['password']
    rol = request.form.get('rol') == 'admin'  # Ejemplo para determinar el rol

    agregar_usuario(username, password, rol)
    flash("Usuario agregado exitosamente")
    return redirect(url_for('index'))



# -------------------------------------------------LOGOUT---------------------------------------------------------------------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    response = make_response(redirect(url_for('index')))
    response.set_cookie('remember_token', '', expires=0)
    return response































# -------------------------PRODUCTOS--------------------------------
@app.route('/consultar_productos')
def consultar_productos():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        if rol:  # Si rol es TRUE, es un administrador
            conn = db.conectar()
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM info_especifica_producto''')
            datos = cursor.fetchall()
            cursor.close()
            db.desconectar(conn)
            
            return render_template('consultarProductos.html', username=username, rol=rol, datos=datos)
        else:
            flash("No tienes permisos para acceder a esta sección")
            return redirect(url_for('index'))
    else:
        return redirect(url_for('secciones'))

    
@app.route('/consultar_producto')
def consultar_producto():
    conn = db.conectar()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM info_especifica_producto''')
    datos = cursor.fetchall()
    cursor.close()
    db.desconectar(conn)
    return render_template('consultarProducto.html', datos=datos)



@app.route('/registrar_producto')
def registrar_producto():
    return render_template('regProduct.html')

@app.route('/registrar_producto', methods=['POST'])
def registrar_producto_post():
    nombre = request.form['nombre']
    codigo_barras = request.form['codigo_barras']
    precio = request.form['precio']
    stock = request.form['stock']
    descripcion = request.form['descripcion']
    marca = request.form['marca']
    categoria = request.form['categoria']

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
        # Inserta en la tabla producto
        cur.execute("""
            INSERT INTO producto (nombre, codigo_barras, precio, stock, descripcion, marca, imagen)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_producto;
        """, (nombre, codigo_barras, precio, stock, descripcion, marca, ruta_imagen))
        producto_id = cur.fetchone()[0]
        cur.execute("""
            SELECT id_categoria
            FROM categoria
            WHERE nombre = %s;
        """, (categoria,))
        categoria_id = cur.fetchone()
        if categoria_id:
            categoria_id = categoria_id[0]
        else:
            raise ValueError(f"Categoría '{categoria}' no encontrada.")
        cur.execute("""
            UPDATE producto
            SET fk_categoria = %s
            WHERE id_producto = %s;
        """, (categoria_id, producto_id))
        conn.commit()
        return render_template('regProduct.html')
    except Exception as e:
        # En caso de error, deshace la transacción
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        # Cierra el cursor y la conexión
        cur.close()
        db.desconectar(conn)

# EDICION
@app.route('/update1_producto/<int:id_producto>', methods=['GET'])
def update1_producto(id_producto):
    conn = db.conectar()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM info_especifica_producto WHERE "ID" = %s''', (id_producto,))
    datos = cursor.fetchone()
    cursor.close()
    db.desconectar(conn)
    return render_template('editarProduct.html', datos=datos)

@app.route('/update_producto_post/<int:id_producto>', methods=['POST'])
def update_producto_post(id_producto):
    nombre = request.form['nombre']
    codigo_barras = request.form['codigo_barras']
    precio = request.form['precio']
    stock = request.form['stock']
    descripcion = request.form['descripcion']
    marca = request.form['marca']
    categoria = request.form['categoria']
    conn = db.conectar()
    cur = conn.cursor()
    try:
        ruta_imagen = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                ruta_imagen = os.path.join('assets', 'img', filename).replace('\\', '/')

        if ruta_imagen:
            cur.execute('''
                UPDATE producto
                SET nombre=%s, codigo_barras=%s, precio=%s, stock=%s, descripcion=%s, marca=%s, categoria=%s, imagen=%s
                WHERE id_producto = %s
            ''', (nombre, codigo_barras, precio, stock, descripcion, marca, categoria, ruta_imagen, id_producto))
        else:
            cur.execute('''
                UPDATE producto
                SET nombre=%s, codigo_barras=%s, precio=%s, stock=%s, descripcion=%s, marca=%s, categoria=%s
                WHERE id_producto = %s
            ''', (nombre, codigo_barras, precio, stock, descripcion, marca, categoria, id_producto))

        cur.execute("""
            SELECT id_categoria
            FROM categoria
            WHERE nombre = %s;
        """, (categoria,))
        categoria_id = cur.fetchone()
        if categoria_id:
            categoria_id = categoria_id[0]
        else:
            raise ValueError(f"Categoría '{categoria}' no encontrada.")

        cur.execute("""
            UPDATE producto
            SET fk_categoria = %s
            WHERE id_producto = %s;
        """, (categoria_id, id_producto))

        conn.commit()
        return redirect(url_for('consultar_productos'))
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        db.desconectar(conn)


@app.route('/delete_producto/<int:id_producto>', methods=['POST'])
def delete_producto(id_producto):
    conn = db.conectar()
    cursor = conn.cursor()
    try:
        # Asegúrate de que la tabla 'producto' es la correcta
        cursor.execute('DELETE FROM producto WHERE id_producto = %s', (id_producto,))
        conn.commit()
        print(f"Producto con ID {id_producto} eliminado correctamente.")
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar producto: {e}")
    finally:
        cursor.close()
        db.desconectar(conn)
    return redirect(url_for('consultar_productos'))

@app.route('/buscar_producto', methods=['POST'])
def buscar_producto():
    buscar_texto = request.form.get('buscar', '')
    conn = db.conectar()
    try:
        cursor = conn.cursor()
        query = '''SELECT * FROM info_especifica_producto WHERE "Nombre" ILIKE %s OR "ID"::TEXT ILIKE %s'''
        cursor.execute(query, (f'%{buscar_texto}%', f'%{buscar_texto}%'))
        datos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f'Error: {e}')
        datos = []
    finally:
        db.desconectar(conn)
    return render_template('consultarProductos.html', datos=datos)


@app.route('/consultar_usuario/<int:id_usuario>')
def consultar_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        # Verificar que el rol sea 1 (administrador)
        if rol != 1:  # Solo los administradores pueden consultar usuarios
            return jsonify({"error": "Acceso no autorizado"}), 403
        
        # Conectar a la base de datos
        conn = db.conectar()
        cursor = conn.cursor()
        
        # Obtener información general del usuario desde la vista `nombre_usuario`
        cursor.execute('''SELECT * FROM nombre_usuario WHERE "ID" = %s''', (id_usuario,))
        usuario_general = cursor.fetchone()
        
        # Obtener información específica del usuario desde la vista `info_especifica_user`
        cursor.execute('''SELECT * FROM info_especifica_user WHERE "ID" = %s''', (id_usuario,))
        usuario_especifico = cursor.fetchone()
        
        cursor.close()
        db.desconectar(conn)
        
        # Combinar la información general y específica
        usuario = {}
        if usuario_general:
            columns = [desc[0] for desc in cursor.description]
            usuario_general_dict = dict(zip(columns, usuario_general))
            usuario.update(usuario_general_dict)
        
        if usuario_especifico:
            columns = [desc[0] for desc in cursor.description]
            usuario_especifico_dict = dict(zip(columns, usuario_especifico))
            usuario.update(usuario_especifico_dict)
        
        # Renderizar la plantilla con la información del usuario
        return render_template('consultarUsuario.html', username=username, rol=rol, usuario=usuario)
    else:
        return redirect(url_for('login'))

@app.route('/delete_usuario/<int:id_usuario>', methods=['POST'])
def delete_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        session_rol = session['rol']
        
        # Verificar que el rol sea 1 (administrador)
        if session_rol != 1:
            return jsonify({"error": "Acceso no autorizado"}), 403
        
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
            return jsonify({"error": "No se pudo eliminar el usuario"}), 500
        finally:
            cursor.close()
            db.desconectar(conn)
        
        return redirect(url_for('consultar_usuarios'))
    else:
        return redirect(url_for('secciones'))