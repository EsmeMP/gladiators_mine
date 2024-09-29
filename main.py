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
from flask import send_file, abort
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
import os

from flask import send_file, render_template, request, session, redirect, url_for, jsonify
from fpdf import FPDF
import io
from fpdf import FPDF
import io
from flask import send_file, session, redirect, url_for, render_template, request, jsonify
from flask import Flask, send_file, session, redirect, url_for, render_template, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash


app = Flask(__name__)
app.secret_key = 'super_secret_key'
serializer = URLSafeTimedSerializer(app.secret_key)


# UPLOAD_FOLDER = os.path.join('assets', 'img')
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def actualizar_contraseñas():
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

        # Leer las contraseñas existentes
        cursor.execute("SELECT username, password FROM usuario")
        usuarios = cursor.fetchall()

        # Encriptar las contraseñas y actualizar la base de datos
        for username, password in usuarios:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "UPDATE usuari SET password = %s WHERE username = %s",
                (hashed_password, username)
            )

        connection.commit()
        print("Contraseñas actualizadas exitosamente")

    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a la base de datos", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

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
        remember_me = request.form.get('remember')

        resultado = verificar_credenciales(username, password)
        if resultado is not None:
            session['usuario_id'] = resultado[0]
            session['nombre_completo'] = resultado[1]
            session['username'] = resultado[2]
            session['rol'] = resultado[4]

            print(f"Rol del usuario autenticado: {session['rol']}")
            flash(f"Rol del usuario autenticado: {session['rol']}")
            if session['rol'] == 1:
                print("El usuario es un administrador.")
            elif session['rol'] == 2:
                print("El usuario es un usuario estándar.")
            else:
                print("El rol del usuario es indefinido o incorrecto.")



            if remember_me:
                token = serializer.dumps(username, salt='remember-me')
                response = make_response(redirect(url_for('secciones')))
                response.set_cookie('remember_token', token, max_age=60*60*24*30)
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

        if rol == 1:
            return render_template('secciones.html', username=username, rol=True)
        else:
            return render_template('secciones.html', username=username, rol=False)
    else:
        return redirect(url_for('login'))



@app.before_request
def before_request():
    print("Sesión actual:", session)


# ---------------------------------PRODUCTOS-----------------------------------------------------------------------------
@app.route('/productos')
def productos():
    if 'username' in session and 'rol' in session:
        rol = session['rol']
        if rol == 1:
            username = session['username']
            return render_template('regProduct.html', username=username, rol=rol)
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_productos'))
    else:
        return redirect(url_for('login'))

@app.route('/registrar_producto', methods=['POST'])
def registrar_producto_post():
    if 'username' in session and 'rol' in session:
        rol = session['rol']
        if rol == 1:

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
                return redirect(url_for('consultar_productos'))
            except Exception as e:
                conn.rollback()
                flash(f"Error: {e}")
                return redirect(url_for('registrar_producto'))
            finally:
                cur.close()
                db.desconectar(conn)
        else:
            flash("No tienes permisos para registrar productos", 'danger')
            return redirect(url_for('consultar_productos'))
    else:
        return redirect(url_for('login'))


@app.route('/consultar_productos')
def consultar_productos():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        conn = db.conectar()
        cursor = conn.cursor()

        if rol:
            cursor.execute('''SELECT * FROM info_especifica_producto ORDER BY "ID"''')
        else:
            cursor.execute('''SELECT * FROM info_especifica_producto ORDER BY "ID"''')
        datos = cursor.fetchall()
        cursor.close()
        db.desconectar(conn)
        
        return render_template('consultarProductos.html', username=username, rol=rol, datos=datos)
    else:
        return redirect(url_for('secciones'))


@app.route('/consultar_producto/<int:id_producto>')
def consultar_producto(id_producto):

    if 'username' in session and 'rol' in session:
        rol = session['rol']
        
        if rol == 1:
            try:

                conn = db.conectar()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM info_especifica_producto WHERE "ID" = %s', (id_producto,))
                datos = cursor.fetchall()
                
                cursor.close()
                db.desconectar(conn)
                
                if not datos:
                    flash("No se encontraron datos para el producto solicitado.", 'warning')
                    return redirect(url_for('consultar_productos'))
                
                return render_template('consultarProducto.html', datos=datos)
            
            except Exception as e:

                flash(f"Error al consultar el producto: {e}", 'danger')
                return redirect(url_for('consultar_productos'))
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_productos'))
    else:
        flash("Debes iniciar sesión para acceder a esta sección", 'warning')
        return redirect(url_for('login'))




@app.route('/update1_producto/<int:id_producto>', methods=['GET'])
def update1_producto(id_producto):
    if 'username' in session and 'rol' in session:
        rol = session['rol']
        
        if rol == 1:
            conn = db.conectar()
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM info_especifica_producto WHERE "ID" = %s''', (id_producto,))
            datos = cursor.fetchone()
            cursor.close()
            db.desconectar(conn)
            return render_template('editarProduct.html', datos=datos)
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_productos'))
    else:
        return redirect(url_for('login'))



@app.route('/update_producto_post/<int:id_producto>', methods=['POST'])
def update_producto_post(id_producto):
    if 'username' in session and 'rol' in session:
        rol = session['rol']
        
        if rol == 1:
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
                conn = db.conectar()
                cursor = conn.cursor()
                cursor.execute('''SELECT imagen FROM producto WHERE id_producto = %s''', (id_producto,))
                ruta_imagen = cursor.fetchone()[0]
                cursor.close()
                db.desconectar(conn)

            conn = db.conectar()
            cur = conn.cursor()
            try:
                cur.execute('''SELECT id_categoria FROM categoria WHERE nombre = %s''', (categoria,))
                categoria_id = cur.fetchone()
                if categoria_id:
                    categoria_id = categoria_id[0]
                else:
                    raise ValueError(f"Categoría '{categoria}' no encontrada.")
                
                update_query = '''
                    UPDATE producto
                    SET nombre = %s, codigo_barras = %s, precio = %s, stock = %s, descripcion = %s, marca = %s, imagen = %s, fk_categoria = %s
                    WHERE id_producto = %s
                '''
                params = (nombre, codigo_barras, precio, stock, descripcion, marca, ruta_imagen, categoria_id, id_producto)
                cur.execute(update_query, params)
                conn.commit()
                flash("Producto actualizado exitosamente.")
                return redirect(url_for('consultar_productos'))
            except Exception as e:
                conn.rollback()
                flash(f"Error al actualizar producto: {e}")
                return redirect(url_for('consultar_productos'))
            finally:
                cur.close()
                db.desconectar(conn)
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_productos'))
    else:
        return redirect(url_for('login'))


@app.route('/delete_producto/<int:id_producto>', methods=['POST'])
def delete_producto(id_producto):
    conn = db.conectar()
    cursor = conn.cursor()
    try:
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


# ---------------------------------------------------------VENTAS---------------------------------------------------------------



@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    conn = conectar()
    cursor = conn.cursor()

    numero_venta = None
    total = 0.0

    nombre_completo = session.get('nombre_completo') 

    if request.method == 'POST':
        try:
            venta_actual = request.form.get('venta_actual')
            if venta_actual:
                venta_actual = json.loads(venta_actual)
                print("Productos en la venta actual:", venta_actual)  # Debug

                if not venta_actual:
                    flash("No hay productos en la venta actual.")
                    return redirect(url_for('registrar_venta'))

                # Obtener el ID del usuario y el nombre completo del usuario desde la sesión
                fk_usuario = session.get('usuario_id')
                nombre_completo = session.get('nombre_completo')

                # Verificar que el usuario esté autenticado
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
            desconectar(conn)

    else:  # Para método GET
        cursor.execute("SELECT COALESCE(MAX(id_venta) + 1, 1) FROM venta")
        numero_venta = cursor.fetchone()[0]

    cursor.close()
    desconectar(conn)

    return render_template('regVenta.html', numero_venta=numero_venta, total=total, usuario=nombre_completo)



@app.route('/generar_ticket', methods=['POST'])
def generar_ticket():
    try:
        # Obtener datos del request
        efectivo_recibido = float(request.form.get('efectivo_recibido', 0.00))
        vuelto = efectivo_recibido - float(request.form.get('total', 0.00))
        monto_efectivo = efectivo_recibido
        subtotal = float(request.form.get('subtotal', 0.00))
        total = float(request.form.get('total', 0.00))

        # Configuración del PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        styles = getSampleStyleSheet()
        style_normal = styles["Normal"]
        style_heading = styles["Heading1"]

        # Cargar el logotipo
        logo_path = "static/assets/img/Logotipo_GladiatorRedondo.png"

        if os.path.exists(logo_path):
            img = Image(logo_path)
            img.drawHeight = 0.5 * inch
            img.drawWidth = 0.5 * inch
            elementos = [img]
        else:
            abort(404, description="Logotipo no encontrado")

        # Añadir número de venta
        elementos.append(Spacer(1, 12))
        elementos.append(Paragraph(f"<b>No. Venta:</b> 00000076", style_normal))

        elementos.append(Spacer(1, 12))

        # Añadir título
        elementos.append(Paragraph("<b>Efectivo recibido</b>", style_heading))
        elementos.append(Paragraph(f"{efectivo_recibido:.2f}", style_heading))

        elementos.append(Spacer(1, 12))

        # Crear tabla de datos
        data = [
            ["Vuelto:", f"${vuelto:.2f}"],
            ["Monto Efectivo:", f"${monto_efectivo:.2f}"],
            ["Subtotal:", f"${subtotal:.2f}"],
            ["Total:", f"${total:.2f}"],
        ]

        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elementos.append(table)

        # Añadir total al final en grande
        elementos.append(Spacer(1, 36))
        elementos.append(Paragraph(f"<b>Total: ${total:.2f}</b>", style_heading))

        # Construir y retornar el PDF
        doc.build(elementos)
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name='ticket.pdf', mimetype='application/pdf')

    except Exception as e:
        print(f"Error generando el ticket: {e}")
        abort(500, description="Error generando el ticket")

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



# @app.route('/reporte_diario')
# def reporte_diario():
#     if 'username' in session and 'rol' in session:
#         username = session['username']
#         rol = session['rol']

#         # Permitir acceso a usuarios con rol 1 (administrador) o rol 2 (cajero)
#         if rol in [1, 2]:
#             fecha = request.args.get('fecha')
#             # Obtiene la fecha seleccionada del formulario
#             print(f"Fecha seleccionada: {fecha}")
#             conn = db.conectar()
#             cursor = conn.cursor()
            
#             if fecha:
#                 # Realiza la consulta filtrando por la fecha seleccionada
#                 cursor.execute('''
#                     SELECT *
#                     FROM reporte_diario
#                     WHERE fecha = %s
#                 ''', (fecha,))
#             else:
#                 # Si no se ha seleccionado una fecha, muestra todas las ventas
#                 cursor.execute('SELECT * FROM reporte_diario')
            
#             datos = cursor.fetchall()
            
#             if datos:
#                 # Calcular el total de las ventas
#                 total = sum([fila[3] for fila in datos])
#             else:
#                 total = 0
            
#             cursor.close()
#             db.desconectar(conn)
            
#             # Renderiza la plantilla con los datos del reporte diario y el total
#             return render_template('repDiario.html', datos=datos, total=total)
#         else:
#             return jsonify({"error": "Acceso no autorizado"}), 403
#     else:
#         return redirect(url_for('login'))

@app.route('/reporte_diario')
def reporte_diario():
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        if rol in [1, 2]:
            fecha = request.args.get('fecha')
            conn = db.conectar()
            cursor = conn.cursor()
            
            if fecha:
                cursor.execute('''
                    SELECT *
                    FROM reporte_diario
                    WHERE fecha = %s
                ''', (fecha,))
            else:
                cursor.execute('SELECT * FROM reporte_diario')
            
            datos = cursor.fetchall()
            
            if datos:
                total = sum([fila[3] for fila in datos])
            else:
                total = 0
            
            cursor.close()
            db.desconectar(conn)
            
            # Generar el PDF del reporte diario
            pdf = FPDF()
            pdf.add_page()
            
            # Ruta del logotipo
            logo_path = "static/assets/img/Logotipo_GladiatorRedondo.png"
            
            # Verificar si el archivo de logotipo existe
            if os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, x=(210-33)/2, y=8, w=33)
                except Exception as e:
                    print(f"Error al cargar la imagen: {e}")
            else:
                print(f"Logotipo no encontrado en la ruta: {logo_path}")
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, txt="Logotipo no encontrado", ln=True, align='C')
            
            # Título del reporte
            pdf.ln(20)  # Espacio después del logotipo o texto alternativo
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Reporte Diario", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Fecha: {fecha if fecha else 'Todas las fechas'}", ln=True, align='C')
            pdf.ln(10)
            
            # Encabezados de la tabla
            pdf.cell(40, 10, txt="ID Venta", border=1)
            pdf.cell(60, 10, txt="Fecha", border=1)
            pdf.cell(40, 10, txt="Hora", border=1)
            pdf.cell(40, 10, txt="Total", border=1)
            pdf.ln()

            # Añadir los datos al PDF
            for fila in datos:
                pdf.cell(40, 10, txt=str(fila[0]), border=1)
                pdf.cell(60, 10, txt=str(fila[1]), border=1)
                pdf.cell(40, 10, txt=str(fila[2]), border=1)
                pdf.cell(40, 10, txt=str(fila[3]), border=1)
                pdf.ln()
            
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Total: ${total:.2f}", ln=True, align='R')
            
            # Guardar el PDF en un buffer en memoria
            pdf_output = io.BytesIO()
            pdf_output.write(pdf.output(dest='S').encode('latin1'))
            pdf_output.seek(0)
            
            # Guardar el buffer en la sesión para usarlo más adelante
            session['pdf_output'] = pdf_output.getvalue()
            
            # Renderizar la plantilla y mostrar los datos
            return render_template('repDiario.html', datos=datos, total=total)
        else:
            return jsonify({"error": "Acceso no autorizado"}), 403
    else:
        return redirect(url_for('login'))

@app.route('/descargar_reporte')
def descargar_reporte():
    pdf_output = session.get('pdf_output')
    if not pdf_output:
        return redirect(url_for('reporte_diario'))  # Redirige si no hay PDF en la sesión

    # Convertir el contenido de la sesión en un BytesIO para ser enviado
    pdf_buffer = io.BytesIO(pdf_output)
    
    # Descarga el archivo PDF
    return send_file(pdf_buffer, as_attachment=True, download_name='reporte_diario.pdf', mimetype='application/pdf')





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


# @app.route('/reporte_semanal', methods=['GET'])
# def reporte_semanal():
#     if 'username' in session and 'rol' in session:
#         username = session['username']
#         rol = session['rol']

#         if rol in [1, 2]:
#             fecha1 = request.args.get('fecha1')
#             fecha2 = request.args.get('fecha2')

#             if not fecha1 or not fecha2:
#                 fecha1 = "default_start_date"
#                 fecha2 = "default_end_date"

#             # Conectar a la base de datos y obtener los datos
#             conn = db.conectar()
#             cursor = conn.cursor()

#             if fecha1 and fecha2:
#                 cursor.execute('''SELECT * FROM reporte_diario WHERE fecha BETWEEN %s AND %s''', (fecha1, fecha2,))
#             else:
#                 cursor.execute('SELECT * FROM reporte_diario')

#             datos = cursor.fetchall()
#             total = sum([fila[3] for fila in datos]) if datos else 0

#             cursor.close()
#             db.desconectar(conn)

#             # Crear el PDF
#             pdf = FPDF()
#             pdf.add_page()

#             logo_path = "static/assets/img/Logotipo_GladiatorRedondo.png"

#             if os.path.exists(logo_path):
#                 pdf.image(logo_path, x=(210-33)/2, y=8, w=33)
#             else:
#                 pdf.set_font("Arial", 'B', 12)
#                 pdf.cell(200, 10, txt="Logotipo no encontrado", ln=True, align='C')

#             pdf.ln(20)
#             pdf.set_font("Arial", size=12)
#             pdf.cell(200, 10, txt="Reporte Semanal", ln=True, align='C')
#             pdf.cell(200, 10, txt=f"Fechas: {fecha1} - {fecha2}", ln=True, align='C')
#             pdf.ln(10)

#             pdf.cell(40, 10, txt="ID Venta", border=1)
#             pdf.cell(60, 10, txt="Fecha", border=1)
#             pdf.cell(40, 10, txt="Hora", border=1)
#             pdf.cell(40, 10, txt="Total", border=1)
#             pdf.ln()

#             for fila in datos:
#                 pdf.cell(40, 10, txt=str(fila[0]), border=1)
#                 pdf.cell(60, 10, txt=str(fila[1]), border=1)
#                 pdf.cell(40, 10, txt=str(fila[2]), border=1)
#                 pdf.cell(40, 10, txt=str(fila[3]), border=1)
#                 pdf.ln()

#             pdf.ln(10)
#             pdf.cell(200, 10, txt=f"Total: ${total:.2f}", ln=True, align='R')

#             # Asegurarse de que la carpeta temp_pdfs existe
#             temp_dir = "temp_pdfs"
#             if not os.path.exists(temp_dir):
#                 os.makedirs(temp_dir)

#             # Guardar el PDF en un archivo temporal en el servidor
#             filename = f"reporte_semanal_{fecha1}_a_{fecha2}.pdf"
#             filepath = os.path.join(temp_dir, secure_filename(filename))
#             pdf.output(filepath, 'F')

#             session['pdf_filepath'] = filepath  # Guardar la ruta en la sesión

#             return render_template('repSemanal.html', datos=datos, total=total)
#         else:
#             return jsonify({"error": "Acceso no autorizado"}), 403
#     else:
#         return redirect(url_for('login'))


# @app.route('/descargar_reporte_semanal')
# def descargar_reporte_semanal():
#     pdf_filepath = session.get('pdf_filepath')
#     if not pdf_filepath or not os.path.exists(pdf_filepath):
#         return redirect(url_for('reporte_semanal'))  # Redirige si no hay PDF en la sesión

#     return send_file(pdf_filepath, as_attachment=True, download_name=os.path.basename(pdf_filepath), mimetype='application/pdf')





@app.route('/consulta_venta/<int:id>')
def consulta_venta(id):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']

        if rol in [1, 2]:
            conn = db.conectar()
            cursor = conn.cursor()

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
        
        if rol == 1:
            if request.method == 'POST':
                required_fields = [
                    'nombre', 'apellido_paterno', 'apellido_materno', 'domicilio',
                    'numero_telefonico', 'curp', 'date', 'correo_electronico',
                    'nombre_usuario', 'contraseña', 'tipos_de_usuario'
                ]
                
                for field in required_fields:
                    if field not in request.form:
                        return jsonify({"error": f"Missing field: {field}"}), 400

                numero_telefono = request.form['numero_telefonico']

                # Validar que el número de teléfono tenga como máximo 12 dígitos
                if len(numero_telefono) > 12:
                    flash("El número de teléfono debe tener como máximo 12 dígitos", 'danger')
                    return redirect(url_for('registrar_usuario'))
                
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

                # Encriptar la contraseña antes de guardarla en la base de datos
                hashed_password = generate_password_hash(password)

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
                    
                    # Inserta en usuario utilizando el ID generado y la contraseña encriptada
                    cur.execute("""
                        INSERT INTO usuario (fk_info_empleado, username, password, rol)
                        VALUES (%s, %s, %s, %s);
                    """, (nuevo_id_empleado, username, hashed_password, rol_booleano))
                    
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
        cursor.execute('SELECT * FROM consulta_general ORDER BY id')
        datos = cursor.fetchall()
        
        # Cerrar cursor y conexión
        cursor.close()
        db.desconectar(conn)
        
        # Renderizar la plantilla con datos del usuario y resultados de la consulta
        return render_template('consultarUsuarios.html', username=username, rol=rol, datos=datos)
    else:
        return redirect(url_for('secciones'))


@app.route('/consultar_usuario/<int:id_usuario>')
def consultar_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        if rol == 1:  # Solo administradores (rol == 1)
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
        else:
            flash("No tienes permisos para acceder a esta sección", 'danger')
            return redirect(url_for('consultar_usuarios'))
    else:
        return redirect(url_for('login'))


@app.route('/update1_usuario/<int:id_usuario>', methods=['GET'])
def update1_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        username = session['username']
        rol = session['rol']
        
        if rol == 1:
            conn = db.conectar()
            cursor = conn.cursor()
            
            # Utiliza la vista 'edicion_user' para obtener los datos necesarios
            cursor.execute('''SELECT * FROM info_especifica_user 
                              WHERE "ID" = %s''', (id_usuario,))
            
            datos = cursor.fetchone()
            
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
    buscar_texto = request.form.get('buscar', '')
    conn = db.conectar()
    try:
        cursor = conn.cursor()
        query = '''SELECT * FROM consulta_general WHERE nombre ILIKE %s OR id::TEXT ILIKE %s'''
        cursor.execute(query, (f'%{buscar_texto}%', f'%{buscar_texto}%'))
        datos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f'Error: {e}')
        datos = []
    finally:
        db.desconectar(conn)
    return render_template('consultarUsuarios.html', datos=datos)

    
@app.route('/delete_usuario/<int:id_usuario>', methods=['POST'])
def delete_usuario(id_usuario):
    if 'username' in session and 'rol' in session:
        session_rol = session['rol']
        
        if session_rol != 1:
            return jsonify({"error": "Acceso no autorizado"}), 403
        
        conn = db.conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''SELECT fk_info_empleado FROM usuario WHERE id_usuario = %s''', (id_usuario,))
            fk_info_empleado = cursor.fetchone()[0]
            
            cursor.execute('''DELETE FROM usuario WHERE id_usuario = %s''', (id_usuario,))
            
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
    rol = request.form.get('rol') == 'admin'

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
