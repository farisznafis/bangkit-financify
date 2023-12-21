# CC-Financify
## Financify Cloud Computing :
  - App's infrastructure is Google Cloud with Python as the primary language, and Flask serves as the framework for our API. Acting as a bridge for user input, our API facilitates machine learning training and output generation. The entire codebase is encapsulated in a Docker image, which is then pushed to the Google Cloud Container Registry. Once the Docker image is in the container registry, we deploy it via Cloud Run, thus allowing access for the mobile development team.

  - Tools needed:
      - Python 3.9
      - Google Cloud Platform

## Team Member:
    - Mochammad Shandy Ferdiansyach c008bsy3771@bangkit.academy	
    - Herdian Aji Laksana c159bsy3680@bangkit.academy

## The Cloud Computing team's main responsibility is to 
    -  Develop APIs used by Mobile applications, manage server resources, and be the bridge between Mobile Development and Machine Learning.

## Installation
  notes : For the machine learning model, we using Cloud Run with Tensorflow and API framework Flask.

  1. Make a GCP Project
  2. Configure IAM and Admin
  3. Install the cloud SDK
  4. Make an API for predict
  5. Build a Dockerfile
  6. Deploy using Cloud Run