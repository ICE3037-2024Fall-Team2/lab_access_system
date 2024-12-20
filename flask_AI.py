from flask import Flask, request, jsonify
from deepface import DeepFace
import boto3
from mtcnn import MTCNN
import pymysql
import cv2
import numpy as np
import datetime
import requests
from botocore.exceptions import ClientError
from flask_cors import CORS
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, S3_BUCKET_NAME, DB_CONFIG
import json

app = Flask(__name__)
CORS(app)

# Initialize ArcFace model
model_name = "ArcFace"
model = DeepFace.build_model(model_name)

# S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)

bucket_name = S3_BUCKET_NAME

# Database configuration
db_config = DB_CONFIG

# Matching threshold
threshold = 1


def generate_presigned_url(s3_client, bucket_name, object_key, expiration=3600):
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        app.logger.error(f"Error generating presigned URL: {e}")
        return None

def crop_face(image):
    detector = MTCNN()
    results = detector.detect_faces(image)
    if results:
        largest_face = max(results,key=lambda x: x['box'][2] * x['box'][3])
        x,y,width,height = largest_face['box']
        x,y = max(0,x), max(0,y)
        cropped_face = image[y:y + height, x:x + width]
        return cv2.resize(cropped_face, (112,112))
    return None

def calculate_feature(image):
    try:
        #cropped_face = crop_face(image)
        #if cropped_face is None:
            #app.logger.warning("No face detected in the image")
            #return None
        embedding = DeepFace.represent(image, model_name=model_name, enforce_detection=False)
        if isinstance(embedding, list) and len(embedding) > 0:
            return np.array(embedding[0]["embedding"], dtype=np.float32) 
        else:
            raise ValueError("Invalid embedding format")
    except Exception as e:
        app.logger.error(f"Error calculating feature: {e}")
        return None


def parse_from_request(request):
    try:
        file = request.files.get('image')
        if not file or file.filename == '':
            raise ValueError("No file part in form-data request")

        image_data = file.read()
        lab_id = request.form.get('lab_id')
        if not lab_id:
            raise ValueError("Missing 'lab_id' in form-data request")

        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image")

        return img, lab_id
    except Exception as e:
        app.logger.error(f"Error parsing request: {e}")
        raise


def update_missing_features():
    try:
        with pymysql.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, photo_path FROM user_img WHERE features IS NULL AND photo_path IS NOT NULL")
                missing_features = cursor.fetchall()

                for user_id, photo_path in missing_features:
                    presigned_url = generate_presigned_url(s3_client, bucket_name, photo_path)
                    if not presigned_url:
                        continue

                    response = requests.get(presigned_url)
                    img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    if img is None:
                        app.logger.warning(f"Failed to decode image for user {user_id}")
                        continue

                    feature = calculate_feature(img)
                    if feature is not None:
                        feature_json = json.dumps(feature.tolist())
                        cursor.execute("UPDATE user_img SET features = %s WHERE id = %s", (feature_json, user_id))
                        connection.commit()
    except pymysql.MySQLError as e:
        app.logger.error(f"Database error: {e}")

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        update_missing_features()
        img, lab_id = parse_from_request(request)
        mirr_img = cv2.flip(img,1)
        # Extract embedding from the uploaded image
        input_feature = calculate_feature(img)
        mirr_input_feature = calculate_feature(mirr_img)
        if input_feature is None and mirr_input_feature is None:
            return jsonify({"error": "Feature extraction failed"}), 400

        matched_student_id = None
        min_distance = float("inf")

        with pymysql.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Query all stored features
                cursor.execute("SELECT id, features FROM user_img WHERE features IS NOT NULL")
                students = cursor.fetchall()

                for student_id, features_json in students:
                    # Load features directly from JSON array
                    db_feature = np.array(json.loads(features_json), dtype=np.float32)
                    input_feature = input_feature / np.linalg.norm(input_feature)
                    db_feature = db_feature / np.linalg.norm(db_feature)
                    distance = np.linalg.norm(input_feature - db_feature)
                    mirr_distance = np.linalg.norm(mirr_input_feature - db_feature)
                    #distance = np.dot(input_feature, db_feature)
                    #mirr_distance = np.dot(mirr_input_feature, db_feature)
                    best_distance = min(distance, mirr_distance)
                    print(best_distance)
                    if best_distance < min_distance and best_distance < threshold:
                        min_distance = distance
                        matched_student_id = student_id

                today_date = datetime.date.today()
                cursor.execute("""
                    SELECT user_id, reservation_id, date, time FROM reservations
                    WHERE lab_id = %s AND date = %s AND verified = 1
                """, (lab_id, today_date))
                reservations = cursor.fetchall()
                print(reservations)
                if matched_student_id:
                    print(matched_student_id)
                    for user_id, reservation_id, date, time in reservations:
                        if user_id == matched_student_id:
                            reservation_time = datetime.datetime.strptime(
                                f"{date.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
                            current_time = datetime.datetime.now()
                            time_diff = abs((current_time - reservation_time).total_seconds()) / 60

                            if time_diff <= 5:
                                cursor.execute(
                                    "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                                    (reservation_id,)
                                )
                                connection.commit()
                                return jsonify({"verified": True, "student_id": matched_student_id})
                            else:
                                return jsonify({"verified": False, "message": "Outside the reservation time window"})
                else:
                    return jsonify({"verified": False, "message": "No matching student"})              

        return jsonify({"verified": False, "message": "No upcoming reservation found"})

    except ValueError as e:
        app.logger.error(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, request, jsonify
from deepface import DeepFace
import boto3
from mtcnn import MTCNN
import pymysql
import cv2
import numpy as np
import datetime
import requests
from botocore.exceptions import ClientError
from flask_cors import CORS
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, S3_BUCKET_NAME, DB_CONFIG
import json

app = Flask(__name__)
CORS(app)

# Initialize ArcFace model
model_name = "ArcFace"
model = DeepFace.build_model(model_name)

# S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)

bucket_name = S3_BUCKET_NAME

# Database configuration
db_config = DB_CONFIG

# Matching threshold
threshold = 1


def generate_presigned_url(s3_client, bucket_name, object_key, expiration=3600):
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        app.logger.error(f"Error generating presigned URL: {e}")
        return None

def crop_face(image):
    detector = MTCNN()
    results = detector.detect_faces(image)
    if results:
        largest_face = max(results,key=lambda x: x['box'][2] * x['box'][3])
        x,y,width,height = largest_face['box']
        x,y = max(0,x), max(0,y)
        cropped_face = image[y:y + height, x:x + width]
        return cv2.resize(cropped_face, (112,112))
    return None

def calculate_feature(image):
    try:
        #cropped_face = crop_face(image)
        #if cropped_face is None:
            #app.logger.warning("No face detected in the image")
            #return None
        embedding = DeepFace.represent(image, model_name=model_name, enforce_detection=False)
        if isinstance(embedding, list) and len(embedding) > 0:
            return np.array(embedding[0]["embedding"], dtype=np.float32) 
        else:
            raise ValueError("Invalid embedding format")
    except Exception as e:
        app.logger.error(f"Error calculating feature: {e}")
        return None


def parse_from_request(request):
    try:
        file = request.files.get('image')
        if not file or file.filename == '':
            raise ValueError("No file part in form-data request")

        image_data = file.read()
        lab_id = request.form.get('lab_id')
        if not lab_id:
            raise ValueError("Missing 'lab_id' in form-data request")

        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image")

        return img, lab_id
    except Exception as e:
        app.logger.error(f"Error parsing request: {e}")
        raise


def update_missing_features():
    try:
        with pymysql.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, photo_path FROM user_img WHERE features IS NULL AND photo_path IS NOT NULL")
                missing_features = cursor.fetchall()

                for user_id, photo_path in missing_features:
                    presigned_url = generate_presigned_url(s3_client, bucket_name, photo_path)
                    if not presigned_url:
                        continue

                    response = requests.get(presigned_url)
                    img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    if img is None:
                        app.logger.warning(f"Failed to decode image for user {user_id}")
                        continue

                    feature = calculate_feature(img)
                    if feature is not None:
                        feature_json = json.dumps(feature.tolist())
                        cursor.execute("UPDATE user_img SET features = %s WHERE id = %s", (feature_json, user_id))
                        connection.commit()
    except pymysql.MySQLError as e:
        app.logger.error(f"Database error: {e}")

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        update_missing_features()
        img, lab_id = parse_from_request(request)
        mirr_img = cv2.flip(img,1)
        # Extract embedding from the uploaded image
        input_feature = calculate_feature(img)
        mirr_input_feature = calculate_feature(mirr_img)
        if input_feature is None and mirr_input_feature is None:
            return jsonify({"error": "Feature extraction failed"}), 400

        matched_student_id = None
        min_distance = float("inf")

        with pymysql.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Query all stored features
                cursor.execute("SELECT id, features FROM user_img WHERE features IS NOT NULL")
                students = cursor.fetchall()

                for student_id, features_json in students:
                    # Load features directly from JSON array
                    db_feature = np.array(json.loads(features_json), dtype=np.float32)
                    input_feature = input_feature / np.linalg.norm(input_feature)
                    db_feature = db_feature / np.linalg.norm(db_feature)
                    distance = np.linalg.norm(input_feature - db_feature)
                    mirr_distance = np.linalg.norm(mirr_input_feature - db_feature)
                    #distance = np.dot(input_feature, db_feature)
                    #mirr_distance = np.dot(mirr_input_feature, db_feature)
                    best_distance = min(distance, mirr_distance)
                    print(best_distance)
                    if best_distance < min_distance and best_distance < threshold:
                        min_distance = distance
                        matched_student_id = student_id

                today_date = datetime.date.today()
                cursor.execute("""
                    SELECT user_id, reservation_id, date, time FROM reservations
                    WHERE lab_id = %s AND date = %s AND verified = 1
                """, (lab_id, today_date))
                reservations = cursor.fetchall()
                print(reservations)
                if matched_student_id:
                    print(matched_student_id)
                    for user_id, reservation_id, date, time in reservations:
                        if user_id == matched_student_id:
                            reservation_time = datetime.datetime.strptime(
                                f"{date.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
                            current_time = datetime.datetime.now()
                            time_diff = abs((current_time - reservation_time).total_seconds()) / 60

                            if time_diff <= 5:
                                cursor.execute(
                                    "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                                    (reservation_id,)
                                )
                                connection.commit()
                                return jsonify({"verified": True, "student_id": matched_student_id})
                            else:
                                return jsonify({"verified": False, "message": "Outside the reservation time window"})
                else:
                    return jsonify({"verified": False, "message": "No matching student"})              

        return jsonify({"verified": False, "message": "No upcoming reservation found"})

    except ValueError as e:
        app.logger.error(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
