try:
    import bcrypt as bb
    from dotenv import load_dotenv
    from flask import Flask, request, send_file
    from flask_cors import CORS
    from flask_mail import Mail, Message
    from fpdf import FPDF
    import boto3, datetime, jwt, os, sys, pdb, pymysql, sys, zipfile
    from time import sleep
except Exception as ee:
    print(f'Error when importing python dependencies', file=sys.stderr)
    print(f'ErrorMsg: {ee}', file=sys.stderr)
    sys.exit(1)

load_dotenv()

db_connected = False
connection = None

def get_mysql_connection():
    global connection
    global db_connected
    if (connection):
        print(f'We already have a connection stablished', file=sys.stderr)
        db_connected = True
    else:
        try:
            connection = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            db_connected = True
            print(f'We are now connected to the DB', file=sys.stderr)
        except Exception as ee:
            db_connected = False
            print(f'\nError when trying to connect to db: {ee}', file=sys.stderr)
            sleep(1)
    return connection

# =============================================================================
#   Flask app declaration and config setup
# =============================================================================
app = Flask(__name__, static_folder='./react_server/build', static_url_path='/')
app.config["SECRET_KEY"] = 'jv5(78$62-hr+8==+kn4%r*(9g)fubx&&i=3ewc9p*tnkt6u$h'
# app.config["MAIL_SERVER"] = 'smtp.mail.yahoo.com'
# app.config["MAIL_PORT"] = 465
# app.config["MAIL_USE_SSL"] = True
# app.config["MAIL_USE_TLS"] = False
# app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
# app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
CORS(app)
mail = Mail(app)


# =============================================================================
#   Routes declaration
# =============================================================================
routes = {
    'api_home': '/',
    'api_register': '/register/',
    'api_login': '/login/',
    'api_images': '/images/',
    'api_upload_image': '/image/',
    'api_download_image': '/img/retrieve/'
}


# =============================================================================
#   Connection with Parameter Store
# =============================================================================
try:
    ssm = boto3.client(
        service_name='ssm',
        region_name=os.getenv('CONSOLE_REGION'),
        aws_access_key_id=os.getenv('CONSOLE_ID'),
        aws_secret_access_key=os.getenv('CONSOLE_KEY'),
    )

    APP_ADMIN_NAME = ssm.get_parameter(Name='APP_ADMIN_NAME')['Parameter']['Value']
    BUCKET_NAME_RAW = ssm.get_parameter(Name='BUCKET_NAME_RAW')['Parameter']['Value']
    BUCKET_NAME_DONE = ssm.get_parameter(Name='BUCKET_NAME_DONE')['Parameter']['Value']
    CONSOLE_REGION = os.getenv('CONSOLE_REGION')
    CONSOLE_ID = os.getenv('CONSOLE_ID')
    CONSOLE_KEY = os.getenv('CONSOLE_KEY')
    DB_HOST = ssm.get_parameter(Name='DB_HOST')['Parameter']['Value']
    DB_NAME = ssm.get_parameter(Name='DB_NAME')['Parameter']['Value']
    DB_PASSWORD = ssm.get_parameter(Name='DB_PASSWORD')['Parameter']['Value']
    DB_USER = ssm.get_parameter(Name='DB_USER')['Parameter']['Value']
    print(f'We are connected to SSM', file=sys.stderr)

except Exception as ee:
    print('Error when connecting to Parameter Store', file=sys.stderr)
    print(f'ErrorMsg: {ee}', file=sys.stderr)

# =============================================================================
#   Connection with S3 Bucket
# =============================================================================
try:
    s3 = boto3.client(
        service_name="s3",
        region_name=CONSOLE_REGION,
        aws_access_key_id=CONSOLE_ID,
        aws_secret_access_key=CONSOLE_KEY,
    )
    print(f'Success in connecting to S3 Client', file=sys.stderr)

except Exception as ee:
    print(f'Error connecting to S3 Client', file=sys.stderr)
    print(f'ErrorMsg: {ee}', file=sys.stderr)

# =============================================================================
#   Connection with DB
# =============================================================================

while (not db_connected):
    connection = get_mysql_connection()

# =============================================================================
#   Routes behavior
# =============================================================================
@app.route(routes['api_home'], methods=['GET'])
def api_home():
    # return app.send_static_file('index.html')
    connection = get_mysql_connection()
    if (connection.open):
        print(f'In Home: We are connected to the db',file=sys.stderr)
        print(f'Connection open is {connection.open}',file=sys.stderr)
    return {
        "status": 200,
        "message": "Server up and running"
    }

@app.route(routes['api_login'], methods=['POST'])
def api_login():
    if request.method == 'POST':
        connection = get_mysql_connection()
        try:
            user_email = request.json.get('userEmail')
            user_password = request.json.get('userPassword')
            print(f'We got the user data: {user_email} and {user_password}', file=sys.stderr)

            if (not user_email) or (not user_password):
                raise Exception('Failed to get user data')

            print(f'Line 150: connection open is {connection.open}', file=sys.stderr)
            res = None
            with connection.cursor() as cursor:
                sql = """
                    SELECT cadsystemdb.APPUSER.first_name, 
                            cadsystemdb.APPUSER.last_name, 
                            cadsystemdb.APPUSER.email, 
                            cadsystemdb.APPUSER.password
                    FROM cadsystemdb.APPUSER
                    WHERE cadsystemdb.APPUSER.email = %s AND cadsystemdb.APPUSER.is_verified = 1
                    """
                cursor.execute(sql, [user_email])
                res = cursor.fetchone()
                sleep(0.1)
            connection.commit()
            sleep(0.1)

            if (res):
                print(f'We got a user that matches the email', file=sys.stderr)

                if (bb.checkpw(user_password.encode('utf-8'), res['password'].encode('utf-8'))):
                    token = jwt.encode({
                        'user': user_email,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
                    }, app.config['SECRET_KEY'])
                    print(f'Loggin successful', file=sys.stderr)
                    
                    return {
                        'status': 200,
                        'message': 'Login successful',
                        'email': user_email,
                        'token': token
                    }
                else:
                    print(f'Password is incorrect', file=sys.stderr)
            print(f'Logging failed', file=sys.stderr)

            return {
                'status': 402,
                'message': 'Credentials are not valid'
            }
        except Exception as ee:
            print(f'Error: {ee}', file=sys.stderr)
            return {
                'status': 400,
                'message': f'Error: {ee}'
            }

@app.route(routes['api_images'], methods=['POST'])
def api_images():
    if request.method == 'POST':
        connection = get_mysql_connection()
        try:
            user_email = request.json.get('userEmail')
            if not user_email:
                raise Exception('Failed to get user data')
            
            images = []
            with connection.cursor() as cursor:
                sql = """SELECT ii.id, 
                    ii.name, 
                    ii.detection,
                    ii.prediction_level,
                    ii.pathology,
                    ii.birads_score,
                    ii.shape
                    FROM cadsystemdb.IMAGE as ii, cadsystemdb.APPUSER as u
                    WHERE u.id = ii.user_id and u.email = %s
                """
                cursor.execute(sql, [user_email])
                for elem in cursor:
                    images.append({
                            'id': elem['id'],
                            'name': elem['name'],
                            'detection': f"{elem['detection']:0.2f}" if elem['detection'] else None,
                            'predictionLevel': elem['prediction_level'],
                            'pathology': elem['pathology'],
                            'biradsScore': elem['birads_score'],
                            'shape': elem['shape']
                        })
            connection.commit()
            print('Got images from DB')
            return {
                'status': 200,
                'images': images
            }

        except Exception as ee:
            return {
                'status': 400,
                'message': f'Error: {ee}'
            }

@app.route(routes['api_upload_image'], methods=['POST'])
def api_upload_images():
    if request.method == 'POST':
        connection = get_mysql_connection()
        print(f'Connection after function', file=sys.stderr)
        print(connection, file=sys.stderr)
        ret = {
            'status': 200,
            'message' : "Image uploaded successfully",
            'code': -1
        }
        try:
            user_email = request.values.get('userEmail')
            print(f'Line 256: we received user_email={user_email}', file=sys.stderr)
            
            if not user_email:
                print(f'Line 259: we failed to ger user data', file=sys.stderr)
                raise Exception('Failed to get user data')
            
            if (request.files):
                print(request, file=sys.stderr)
                print(request.files, file=sys.stderr)
                uploaded_file = request.files['file']
                print(f'We received a file: {uploaded_file.filename}', file=sys.stderr)
                # pdb.set_trace()
                sleep(0.1)
                with connection.cursor() as cursor:
                        sql = """INSERT INTO IMAGE(name, user_id)VALUES(
                            %s,
                            (SELECT u.id
                            FROM cadsystemdb.APPUSER as u
                            WHERE u.email=%s)
                        )
                        """
                        cursor.execute(sql, [uploaded_file.filename, user_email])
                        ret['code'] = cursor.lastrowid
                connection.commit()

                ######
                # Save image into S3 AWS bucket
                ######
                print(f'Line 284: We are about to upload the file to the S3', file=sys.stderr)
                try:
                    s3.upload_fileobj(
                        uploaded_file,
                        BUCKET_NAME_RAW,
                        f'{user_email}/{ret["code"]}_{uploaded_file.filename}',
                        ExtraArgs={
                            "ContentType": uploaded_file.content_type,
                            # "Metadata": {'mykey': os.getenv('CONSOLE_KEY')}
                        }
                    )

                except Exception as ee:
                    print(f'Line 297: smth went wrong and we need to delete the last inserted image', file=sys.stderr)
                    if (ret['code'] != -1):
                        with connection.cursor() as cursor:
                            sql = """DELETE FROM cadsystemdb.IMAGE WHERE id=%s"""
                            cursor.execute(sql, [str(ret['code'])])
                            ret['code'] = cursor.lastrowid
                        connection.commit()
                    ret = {
                        'status': 403,
                        'message' : "Error when saving image in S3 bucket"
                    }
                    print(f'Error. {ee}', file=sys.stderr)


                ######
                # Send Email
                ######

                return ret

        except Exception as ee:
            return {
                'status': 400,
                'message': f'Error: {ee}'
            }

@app.route(routes['api_download_image'], methods=['POST'])
def retrieve_image():
    if request.method == 'POST':
        try:
            connection = get_mysql_connection()
            print('Line 328: We got good connection with the DB', file=sys.stderr)
            ret = {
                'status': 403,
                'message' : "Image not found",
                'code': -1
            }
            imgcode = request.form['imgcode']
            user_email = request.form['user_email']
            print(f'Line 336: Imgcode: is {imgcode}, by user {user_email}', file=sys.stderr)
            res = None
            # search for the file in the database
            with connection.cursor() as cursor:
                sql = """
                    SELECT * FROM cadsystemdb.IMAGE as im
                    WHERE im.id = %s
                    """
                cursor.execute(sql, [imgcode])
                res = cursor.fetchone()
                print('TENEMOS ALGO EN RES', file=sys.stderr)
                print(res, file=sys.stderr)
            connection.commit()

            # if it does NOT exist
            if (not res):
                print(f"\nRequested file id does not exist in database\n", file=sys.stderr)
                # return ret

            # if exists
            # find it in bucket and retrieve
            name = res['name'].split('.')[0]
            extension = res['name'].split('.')[1]
            
            s3_file_name = f"{user_email}/{imgcode}_{name}.{extension}"
            host_file_name = f'{name}.{extension}'
            s3.download_file(BUCKET_NAME_DONE, s3_file_name, host_file_name)
            
            s3_file_name = f"{user_email}/{imgcode}_{name}_countour.{extension}"
            host_file_name = f'{name}_countour.{extension}'
            s3.download_file(BUCKET_NAME_DONE, s3_file_name, host_file_name)
            
            s3_file_name = f"{user_email}/{imgcode}_{name}_detected.{extension}"
            host_file_name = f'{name}_detected.{extension}'
            s3.download_file(BUCKET_NAME_DONE, s3_file_name, host_file_name)
            
            s3_file_name = f"{user_email}/{imgcode}_{name}_segmented.{extension}"
            host_file_name = f'{name}_segmented.{extension}'
            s3.download_file(BUCKET_NAME_DONE, s3_file_name, host_file_name)
            
            s3_file_name = f"{user_email}/{imgcode}_{name}_with_bounding_box.{extension}"
            host_file_name = f'{name}_with_bounding_box.{extension}'
            s3.download_file(BUCKET_NAME_DONE, s3_file_name, host_file_name)
            
            pdf = FPDF(format='A4')
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 35)
            initialX = 10
            initialY = 10
            w = 90
            padding = 20
            pdf.cell(
                initialX,
                initialY,
                'Results report'
            )
            pdf.set_y(pdf.get_y()+padding)
            filename = f'{name}'

            pdf.image(f"{filename}_detected.{extension}", x=pdf.get_x(), y=pdf.get_y(), w=w)
            pdf.set_y(pdf.get_y()+w+5)
            pdf.image(f"{filename}_countour.{extension}", x=pdf.get_x(), y=pdf.get_y(), w=w)
            pdf.set_x(25);pdf.set_y(padding+initialY)
            pdf.set_x(pdf.get_x()+w+10)
            pdf.image(f"{filename}_segmented.{extension}", x=pdf.get_x(), y=pdf.get_y(), w=w)
            pdf.set_y(pdf.get_y()+w+5)
            pdf.set_x(pdf.get_x()+w+10)
            pdf.image(f"{filename}_with_bounding_box.{extension}", x=pdf.get_x(), y=pdf.get_y(), w=w)

            pdf.set_font('Helvetica', '', 15)
            pdf.set_x(initialX)
            pdf.set_y(pdf.get_y()+w+7)
            # pdf.multi_cell(0, 8, f"Results presented below\n   #Request: \n   Prediction: \n   Detection: \n   Pathology: \n   BIRADs: \n   Shape: ")
            pdf.multi_cell(0, 8, f"#Request: {res['id']}\nPrediction: {res['prediction_level']}\nDetection: {res['detection']}\nPathology: {res['pathology']}\nBIRADs: {res['birads_score']}\nShape: {res['shape']}")

            pdf.output('results.pdf', 'F')

            return send_file(
                'results.pdf',
                mimetype = 'pdf',
                as_attachment = False,
                last_modified = 0
            )

            # zf = zipfile.ZipFile('download.zip', 'w', zipfile.ZIP_DEFLATED)
            # zf.write(f'{name}.{extension}')
            # zf.write(f'{name}_countour.{extension}')
            # zf.write(f'{name}_detected.{extension}')
            # zf.write(f'{name}_segmented.{extension}')
            # zf.write(f'{name}_with_bounding_box.{extension}')
            # zf.close()
            # # pdb.set_trace()
            # return send_file(
            #     'download.zip', 
            #     mimetype = 'zip', 
            #     # download_name=f'downloads.zip', 
            #     as_attachment=True,
            #     last_modified=0
            #     )
        except Exception as ee:
            print(f'Error: {ee}', file=sys.stderr)
            return None

# =============================================================================
#   Used to run flask server as python script
# =============================================================================
if __name__ == "__main__":
    print(f'Flask application has been started', file=sys.stderr)
    os.system(f'gunicorn --reload -b 0.0.0.0:8080 -w 1 app:app')
