from flask import Flask, request, jsonify
from deepface import DeepFace
import boto3
import pymysql
import cv2
import numpy as np
import datetime
import requests
from botocore.exceptions import ClientError
from flask_cors import CORS
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, S3_BUCKET_NAME, DB_CONFIG

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
threshold = 0.68


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


def parse_from_request(request):
    """Parse image from form-data request."""
    file = request.files.get('image')
    if not file or file.filename == '':
        raise ValueError("No file part in form-data request")

    image_data = file.read()

    # Get lab_id from form-data
    lab_id = request.form.get('lab_id')
    if not lab_id:
        raise ValueError("Missing 'lab_id' in form-data request")

    # Convert image data to numpy array
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image")

    return img, lab_id


@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        img, lab_id = parse_from_request(request)
        mirrored_img = cv2.flip(img, 1)

        # Connect to RDS and fetch students
        with pymysql.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, photo_path FROM user_img")
                students = cursor.fetchall()

                # Query reservations for today
                today_date = datetime.date.today()
                cursor.execute("""
                    SELECT user_id, reservation_id, date, time FROM reservations
                    WHERE lab_id = %s AND date = %s AND verified = 1
                """, (lab_id, today_date))
                reservations = cursor.fetchall()

                if not reservations:
                    return jsonify({"verified": False, "message": "No reservation for this lab today"})

        # Image verification
        matched_student_id = None
        min_distance = float("inf")

        for student_id, photo_path in students:
            presigned_url = generate_presigned_url(s3_client, bucket_name, photo_path)

            if not presigned_url:
                app.logger.warning(f"Failed to generate presigned URL for {photo_path}")
                continue

            try:
                response = requests.get(presigned_url)
                response.raise_for_status()
                img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                db_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if db_img is None:
                    app.logger.warning(f"Failed to decode image from S3: {photo_path}")
                    continue

                if db_img.shape[2] == 4:
                    db_img = cv2.cvtColor(db_img, cv2.COLOR_BGRA2BGR)

            except Exception as e:
                app.logger.warning(f"Error loading image from S3: {photo_path}, Error: {e}")
                continue

            result_original = DeepFace.verify(
                img1_path=img, img2_path=db_img, model_name="ArcFace", enforce_detection=False
            )
            result_mirrored = DeepFace.verify(
                img1_path=mirrored_img, img2_path=db_img, model_name="ArcFace", enforce_detection=False
            )

            best_distance = min(result_original["distance"], result_mirrored["distance"])
            if best_distance < min_distance and best_distance < threshold:
                min_distance = best_distance
                matched_student_id = student_id

        if matched_student_id:
            for user_id, reservation_id, date, time in reservations:
                if user_id == matched_student_id:
                    reservation_time = datetime.datetime.strptime(
                        f"{date.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
                    current_time = datetime.datetime.now()
                    time_diff = abs((current_time - reservation_time).total_seconds()) / 60

                    if time_diff <= 5:  # Valid if within 5 minutes
                        with pymysql.connect(**db_config) as connection:
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                                    (reservation_id,)
                                )
                                connection.commit()
                        return jsonify({"verified": True, "student_id": matched_student_id})

            return jsonify({"verified": False, "message": "No matching reservations found"})

        return jsonify({"verified": False, "message": "No matching student found"})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
