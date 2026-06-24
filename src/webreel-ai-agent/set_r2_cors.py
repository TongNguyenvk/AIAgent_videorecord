import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
    region_name='auto'
)

bucket_name = os.getenv('R2_BUCKET')

cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST', 'DELETE'],
        'AllowedOrigins': ['*'],
        'ExposeHeaders': ['ETag', 'Content-Disposition', 'Content-Length'],
        'MaxAgeSeconds': 3000
    }]
}

try:
    print(f"Setting CORS for bucket: {bucket_name}")
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
    print("CORS rules configured successfully. Now localhost:5173 can fetch videos directly from R2!")
except Exception as e:
    print(f"Error configuring CORS: {e}")
