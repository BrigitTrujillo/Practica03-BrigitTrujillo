from flask import Flask, render_template, request, url_for, flash
from werkzeug.utils import redirect
from werkzeug.utils import secure_filename
import os
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from pymongo import MongoClient

# Carga las variables de entorno desde el archivo .env
load_dotenv()

import os

# ...

S3_BUCKET = os.getenv('S3_BUCKET')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')
S3_REGION = os.getenv('S3_REGION')

s3 = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION
)

# ...


app = Flask(__name__)
# Other configurations...
app.secret_key = os.urandom(24)

app.config['UPLOAD_FOLDER'] = 'uploads'

upload_folder = app.config['UPLOAD_FOLDER']

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)


# Configuración de MongoDB Atlas
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['estudiantes']
collection = db['estudiantes']


def get_next_sequence_value(sequence_name):
    sequence_collection = db['sequences']
    sequence_doc = sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'value': 1}},
        return_document=True,
        upsert=True
    )
    return sequence_doc['value']


@app.route('/estudiantes')
def Index():
    data = collection.find()
    return render_template('index.html', estudiantes=data)


@app.route('/')
def inicio():
    return render_template('inicio.html')


@app.route('/insert', methods=['POST'])
def insert():
    if request.method == "POST":
        flash("Data Inserted Successfully")
        nombre = request.form['nombre']
        edad = request.form['edad']
        dni = request.form['dni']
        telefono = request.form['telefono']
        grado = request.form['grado']

        imagen = request.files['imagen']
        if imagen:
            # Generar un nombre único para la imagen
            filename = str(uuid.uuid4().hex) + secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Upload the image to S3
            try:
                s3.upload_fileobj(imagen, S3_BUCKET, filename)
                image_url = filename
            except NoCredentialsError:
                flash('AWS credentials not available.')
                return redirect(url_for('Index'))

        else:
            filename = None
            image_url = None

        
        id_data = get_next_sequence_value('estudiantes')
        
        # Insertar el registro en la base de datos
        document = {
            '_id': id_data,
            'nombre': nombre,
            'edad': edad,
            'dni': dni,
            'telefono': telefono,
            'grado': grado,
            'imagen': filename,
            'imagen_url': image_url
        }
        collection.insert_one(document)

        return redirect(url_for('Index'))


@app.route('/delete/<int:id_data>', methods=['GET'])
def delete(id_data):
    # Obtener los detalles del estudiante antes de eliminarlo
    # Obtener la imagen_url del registro a eliminar
    document = collection.find_one({'_id': id_data})
    imagen_url = document['imagen_url'] if document else None
    if imagen_url:
        try:
            url_parts = imagen_url.split('/')
            filename = url_parts[-1]
            s3.delete_object(Bucket=S3_BUCKET, Key=filename)
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except NoCredentialsError:
            flash('AWS credentials not available.')

    collection.delete_one({'_id': id_data})
    flash("Data Deleted Successfully")
    return redirect(url_for('Index'))


@app.route('/update', methods=['POST', 'GET'])
def update():
    if request.method == 'POST':
        id_data = int(request.form['id'])
        nombre = request.form['nombre']
        edad = request.form['edad']
        dni = request.form['dni']
        telefono = request.form['telefono']
        grado = request.form['grado']

        imagen = request.files['imagen']
        if imagen:
            # Generar un nombre único para la imagen
            filename = str(uuid.uuid4().hex) + secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Upload the image a S3
            try:
                s3.upload_fileobj(imagen, S3_BUCKET, filename)
                image_url = filename

                
                estudiantes = {
                    'nombre': nombre,
                    'edad': edad,
                    'dni': dni,
                    'telefono': telefono,
                    'grado': grado,
                    'imagen': filename,
                    'imagen_url': image_url
                }
                collection.update_one({'_id': id_data}, {'$set': estudiantes})
            except NoCredentialsError:
                flash('AWS credentials not available.')
                return redirect(url_for('Index'))
        else:
            # Mantener la imagen existente en la base de datos
            estudiantes = {
                'nombre': nombre,
                'edad': edad,
                'dni': dni,
                'telefono': telefono,
                'grado': grado
            }
            collection.update_one({'_id': id_data}, {'$set': estudiantes})

        flash("Data Updated Successfully")
        return redirect(url_for('Index'))


if __name__ == "__main__":
    app.run(debug=True)
