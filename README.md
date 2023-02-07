# uofl-aws-cadsystem-backend
Backend code for CAD system development in AWS

# Build the docker image, locally
docker buildx build . --rm --platform=linux/amd64 -t cadsystemback:v0 && docker run --rm -p 8000:8080 --name=cadsystemback cadsystemback:v0

# Run the docker image, locally
docker run --rm -p 8000:8080 --name=cadsystemback cadsystemback:v0


# Build, Tag and Push docker image to AWS ECR
docker buildx build . --rm --platform=linux/amd64 -t cadsystemback:v0 && docker tag cadsystemback:v0 876837268136.dkr.ecr.us-east-2.amazonaws.com/cadsystemback:v0 && docker push 876837268136.dkr.ecr.us-east-2.amazonaws.com/cadsystemback:v0


# Useful Links
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html

https://rajrajhans.com/2020/06/2-ways-to-upload-files-to-s3-in-flask/